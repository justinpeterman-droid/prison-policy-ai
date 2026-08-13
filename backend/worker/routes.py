"""Cloud Tasks-only worker route and fenced durable job execution."""

from dataclasses import dataclass
from datetime import UTC, datetime
import logging
import re
from typing import Protocol
from uuid import UUID

from flask import Blueprint, jsonify, request
from pydantic import ValidationError
from sqlalchemy import event, select

from backend.identity.audit import AuditEventInput, PostgresAuditWriter
from backend.jobs.service import (
    StaleJobClaim,
    TERMINAL_STATES,
    apply_job_result,
    claim_job,
)
from backend.persistence.database import session_scope
from backend.persistence.models.identity import Account, StaffMember
from backend.persistence.models.jobs import AiJob
from backend.persistence.models.reporting import (
    Incident, Report, ReportAccess, ReportRevision,
)
from backend.reports.revisions import RevisionConflict, save_report
from backend.reports.roster import SqlStaffProvider
from backend.reports import service as report_service
from backend.webapp.api_v1.middleware import Actor
from backend.webapp.api_v1.schemas.reporting import ReportContentV1


logger = logging.getLogger(__name__)
_TASK_NAME = re.compile(
    r"^projects/[A-Za-z0-9_-]+/locations/[A-Za-z0-9_-]+/queues/"
    r"(?P<queue>[A-Za-z0-9_-]+)/tasks/ai-job-"
    r"(?P<job_id>[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12})$",
    re.IGNORECASE,
)
_SAFE_TERMINAL_CODES = frozenset({
    "job_output_invalid", "job_target_invalid", "job_result_conflict",
    "job_authorization_invalid", "job_result_contract_unavailable",
})


class TerminalJobFailure(RuntimeError):
    def __init__(self, code: str):
        if code not in _SAFE_TERMINAL_CODES:
            raise ValueError("terminal job code is not approved")
        self.code = code
        super().__init__(code)


class TransientJobFailure(RuntimeError):
    """A safe signal to Cloud Tasks; its message is never returned or persisted."""


@dataclass(frozen=True)
class JobEngineResult:
    report_content: ReportContentV1 | None = None


class ReportEngine(Protocol):
    def run(self, session, job: AiJob) -> JobEngineResult: ...


class RouteNeutralReportEngine:
    """Adapter over the existing report engine for an already-durable report.

    RP-06 permits optional report binding.  Generation can safely append to
    that report through the shared revision service.  The current RP-06 result
    contract cannot atomically promote classify/extract incident content and
    then pass its unchanged-base check, so those types fail closed rather than
    discard output or bypass revision storage.
    """

    _REPORT_KEY = {
        "first_person": "first_person",
        "supervisor_summary": "supervisor_summary",
        "cover_letter": "cover_letter",
        "disciplinary": "disciplinary",
        "investigation": "investigation",
    }

    def run(self, session, job: AiJob) -> JobEngineResult:
        if job.job_type not in {"generate", "disciplinary"}:
            raise TerminalJobFailure("job_result_contract_unavailable")
        if job.report_id is None:
            raise TerminalJobFailure("job_target_invalid")
        incident = session.get(Incident, job.incident_id)
        report = session.get(Report, job.report_id)
        if incident is None or report is None or report.incident_id != incident.id:
            raise TerminalJobFailure("job_target_invalid")

        payload = {
            "notes": incident.field_notes,
            "category": incident.category or "",
            "slots": incident.extracted_facts,
            "answers": incident.gap_answers,
            "charges": incident.charges,
        }
        provider = SqlStaffProvider(session)
        if job.job_type == "disciplinary":
            payload["reports"] = {
                "first_person": str(report.current_content.get("narrative", "")),
            }
            generated = report_service.generate_disciplinary_report(
                payload, staff_provider=provider,
            )
            key = "disciplinary"
        else:
            generated = report_service.generate_report_set(
                payload, staff_provider=provider,
            )
            report_type = getattr(report.report_type, "value", report.report_type)
            key = self._REPORT_KEY.get(str(report_type))
        reports = generated.get("reports") if isinstance(generated, dict) else None
        narrative = reports.get(key) if isinstance(reports, dict) and key else None
        if not isinstance(narrative, str) or not narrative.strip():
            raise TerminalJobFailure("job_output_invalid")
        raw_warnings = generated.get("markers", [])
        warnings = [str(value)[:500] for value in raw_warnings[:100]] if isinstance(raw_warnings, list) else []
        return JobEngineResult(report_content=ReportContentV1(
            narrative=narrative,
            validation={"style": generated.get("style", {})},
            warnings=warnings,
        ))


class JobProcessor:
    def __init__(
        self, *, session_factory=None, report_engine=None,
        metric_sink=None, now=None,
    ):
        self._session_factory = session_factory or session_scope
        self._engine = report_engine or RouteNeutralReportEngine()
        # Reserved for the reviewed durable provider-risk producer.  RP-06 has
        # no provider-started/possible-acceptance marker, so RP-07 deliberately
        # emits no inferred counter from attempts, retries, or lease expiry.
        self._metric_sink = metric_sink
        self._now = now or (lambda: datetime.now(UTC))

    def _scope(self):
        begin = getattr(self._session_factory, "begin", None)
        return begin() if callable(begin) else self._session_factory()

    @staticmethod
    def _actor(session, job: AiJob) -> Actor:
        account = session.get(Account, job.requested_by_account_id)
        staff = session.get(StaffMember, account.staff_member_id) if account else None
        if (
            account is None or account.status != "active"
            or staff is None or not staff.is_active
        ):
            raise TerminalJobFailure("job_authorization_invalid")
        return Actor(
            account_id=account.id,
            staff_member_id=account.staff_member_id,
            session_id=job.id,
            role=account.role,
            auth_version=account.auth_version,
            must_change_pin=account.must_change_pin,
        )

    @staticmethod
    def _authorize_report_target(session, job: AiJob, actor: Actor) -> Report | None:
        if job.report_id is None:
            return None
        report = session.scalar(
            select(Report).where(Report.id == job.report_id).with_for_update()
        )
        if report is None or report.incident_id != job.incident_id:
            raise TerminalJobFailure("job_target_invalid")
        access = session.scalar(
            select(ReportAccess).where(
                ReportAccess.report_id == report.id,
                ReportAccess.staff_member_id == actor.staff_member_id,
                ReportAccess.revoked_at.is_(None),
            ).with_for_update()
        )
        if access is None:
            raise TerminalJobFailure("job_authorization_invalid")
        return report

    def _mark_terminal(self, job_id: UUID, claim_token: UUID, code: str) -> None:
        fixed = self._now()
        with self._scope() as session:
            job = session.scalar(
                select(AiJob).where(AiJob.id == job_id).with_for_update()
            )
            if job is None or job.state in TERMINAL_STATES:
                return
            if job.state != "running" or job.claim_token != claim_token:
                raise StaleJobClaim("job claim is no longer current")
            account = session.get(Account, job.requested_by_account_id)
            if account is None:
                raise RuntimeError("job requester attribution is unavailable")
            job.state = "failed"
            job.stage = "failed"
            job.error_code = code
            job.completed_at = fixed
            job.claim_token = None
            job.lease_expires_at = None
            PostgresAuditWriter().append(session, AuditEventInput(
                actor_account_id=account.id,
                actor_staff_member_id=account.staff_member_id,
                action="ai.job_failed",
                result="failed",
                request_id=f"job_{job.id}",
                target_type="ai_job",
                target_id=job.id,
                details={
                    "job_id": str(job.id), "job_type": job.job_type,
                    "result_code": code,
                },
                client_version="0.0.0-worker",
            ))

    def _release_transient(self, job_id: UUID, claim_token: UUID) -> None:
        with self._scope() as session:
            job = session.scalar(
                select(AiJob).where(AiJob.id == job_id).with_for_update()
            )
            if job is None or job.state in TERMINAL_STATES:
                return
            if job.state == "running" and job.claim_token == claim_token:
                job.state = "queued"
                job.stage = "queued"
                job.claim_token = None
                job.lease_expires_at = None

    def run(self, job_id: UUID, *, retry_count: int) -> None:
        claimed_at = self._now()
        with self._scope() as session:
            claimed = claim_job(session, job_id, now=claimed_at)
            if claimed is None:
                existing = session.get(AiJob, job_id)
                if existing is not None and existing.state == "running":
                    raise TransientJobFailure("job lease is active")
                return
            claim_token = claimed.claim_token
        if claim_token is None:  # database constraint should make this unreachable
            raise TransientJobFailure("job claim is unavailable")
        try:
            # Persist the stage and authorization decision before calling the
            # provider.  Do not hold row locks (or a write transaction) across
            # a long external model request.
            preflight_at = self._now()
            with self._scope() as session:
                job = session.scalar(
                    select(AiJob).where(AiJob.id == job_id).with_for_update()
                )
                if (
                    job is None or job.state != "running"
                    or job.claim_token != claim_token
                    or job.lease_expires_at is None
                    or job.lease_expires_at <= preflight_at
                ):
                    raise StaleJobClaim("job claim is no longer current")
                actor = self._actor(session, job)
                report = self._authorize_report_target(session, job, actor)
                incident = session.scalar(
                    select(Incident).where(Incident.id == job.incident_id).with_for_update()
                )
                if incident is None:
                    raise TerminalJobFailure("job_target_invalid")
                if incident.current_revision_number != job.base_incident_revision:
                    apply_job_result(
                        session, job.id, job.base_incident_revision,
                        claim_token=claim_token, result_reference={},
                        now=preflight_at, request_id=f"job_{job.id}",
                    )
                    return
                if job.job_type in {"generate", "disciplinary"} and report is None:
                    raise TerminalJobFailure("job_target_invalid")
                if job.job_type == "generate":
                    job.stage = "generating"
            provider_started_at = self._now()
            with self._scope() as session:
                job = session.get(AiJob, job_id)
                if (
                    job is None or job.state != "running"
                    or job.claim_token != claim_token
                    or job.lease_expires_at is None
                    or job.lease_expires_at <= provider_started_at
                ):
                    raise StaleJobClaim("job claim is no longer current")
                result = self._engine.run(session, job)

            # Fence again with the actual post-provider clock.  A result that
            # outlived the 20-minute lease is never committed by the stale
            # worker, even though the provider call may already have billed.
            completed_at = self._now()
            with self._scope() as session:
                job = session.scalar(
                    select(AiJob).where(AiJob.id == job_id).with_for_update()
                )
                if (
                    job is None or job.state != "running"
                    or job.claim_token != claim_token
                    or job.lease_expires_at is None
                    or job.lease_expires_at <= completed_at
                ):
                    raise StaleJobClaim("job claim is no longer current")
                actor = self._actor(session, job)
                report = self._authorize_report_target(session, job, actor)
                incident = session.scalar(
                    select(Incident).where(Incident.id == job.incident_id).with_for_update()
                )
                if incident is None:
                    raise TerminalJobFailure("job_target_invalid")
                if incident.current_revision_number != job.base_incident_revision:
                    apply_job_result(
                        session, job.id, job.base_incident_revision,
                        claim_token=claim_token, result_reference={},
                        now=completed_at, request_id=f"job_{job.id}",
                    )
                    return
                reference: dict[str, object] = {}
                if result.report_content is not None:
                    if report is None:
                        raise TerminalJobFailure("job_target_invalid")
                    # `save_report()` flushes internally and revision rows are
                    # immutable after insert. Attach the durable job FK in the
                    # same INSERT rather than attempting a forbidden update.
                    def attach_job_reference(target_session, _context, _instances):
                        for pending in target_session.new:
                            if (
                                isinstance(pending, ReportRevision)
                                and pending.report_id == report.id
                                and pending.reason == "ai_result"
                            ):
                                pending.source_ai_job_id = job.id

                    event.listen(session, "before_flush", attach_job_reference)
                    try:
                        revision = save_report(
                            session, actor, report.id, result.report_content,
                            report.current_revision_number, "ai_result",
                            request_id=f"job_{job.id}",
                            client_version="0.0.0-worker",
                        )
                    finally:
                        event.remove(session, "before_flush", attach_job_reference)
                    for name in (
                        "fast_model", "pro_model", "model_location",
                        "classification_prompt_sha256",
                        "generation_prompt_sha256",
                    ):
                        setattr(job, name, getattr(revision, name))
                    reference = {"reports": [{
                        "report_id": str(report.id),
                        "revision_number": revision.revision_number,
                    }]}
                apply_job_result(
                    session, job.id, job.base_incident_revision,
                    claim_token=claim_token,
                    result_reference=reference,
                    now=completed_at,
                    request_id=f"job_{job.id}",
                )
        except TerminalJobFailure as error:
            self._mark_terminal(job_id, claim_token, error.code)
            raise
        except RevisionConflict:
            self._mark_terminal(job_id, claim_token, "job_result_conflict")
            raise TerminalJobFailure("job_result_conflict") from None
        except StaleJobClaim:
            raise TransientJobFailure("job claim is no longer current") from None
        except ValidationError:
            self._mark_terminal(job_id, claim_token, "job_output_invalid")
            raise TerminalJobFailure("job_output_invalid") from None
        except Exception:
            # Only explicitly classified validation/auth/content failures are
            # terminal. Unknown database, configuration, SDK, and programming
            # failures stay retryable; collapsing them to a 2xx would lose the
            # durable Cloud Tasks retry boundary.
            self._release_transient(job_id, claim_token)
            raise TransientJobFailure("worker dependency unavailable") from None


def _delivery_metadata(job_id: UUID) -> tuple[bool, int]:
    task_name = request.headers.get("X-CloudTasks-TaskName", "")
    queue_name = request.headers.get("X-CloudTasks-QueueName", "")
    retry_value = request.headers.get("X-CloudTasks-TaskRetryCount", "")
    if not task_name or not queue_name or retry_value == "":
        return False, 0
    match = _TASK_NAME.fullmatch(task_name)
    if (
        match is None or match.group("job_id").lower() != str(job_id)
        or match.group("queue") != queue_name
    ):
        return False, 0
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", queue_name):
        return False, 0
    try:
        retry_count = int(retry_value)
    except ValueError:
        return False, 0
    if not 0 <= retry_count <= 100:
        return False, 0
    return True, retry_count


def create_worker_blueprint(processor) -> Blueprint:
    blueprint = Blueprint("private_worker", __name__)

    @blueprint.post("/internal/jobs/<uuid:job_id>/run")
    def run_job(job_id: UUID):
        metadata_present = all(
            header in request.headers for header in (
                "X-CloudTasks-TaskName", "X-CloudTasks-QueueName",
                "X-CloudTasks-TaskRetryCount",
            )
        )
        valid_metadata, retry_count = _delivery_metadata(job_id)
        if not metadata_present:
            return jsonify({"error": "cloud_tasks_metadata_required"}), 401
        payload = request.get_json(silent=True)
        if (
            not valid_metadata or type(payload) is not dict
            or set(payload) != {"job_id"}
            or payload.get("job_id") != str(job_id)
        ):
            return jsonify({"error": "task_request_invalid"}), 400
        try:
            processor.run(job_id, retry_count=retry_count)
        except TerminalJobFailure:
            return "", 204
        except TransientJobFailure:
            return jsonify({"error": "worker_temporarily_unavailable"}), 503
        return "", 204

    return blueprint


__all__ = [
    "JobEngineResult", "JobProcessor", "TerminalJobFailure",
    "TransientJobFailure", "create_worker_blueprint",
]
