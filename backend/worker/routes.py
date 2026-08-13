"""Cloud Tasks-only worker route and fenced durable job execution."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
import os
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
    Incident,
    IncidentRevision,
    Report,
    ReportAccess,
    ReportRevision,
    ReportType,
)
from backend.reports import service as report_service
from backend.reports.revisions import RevisionConflict, save_incident, save_report
from backend.reports.roster import SqlStaffProvider
from backend.webapp.api_v1.middleware import Actor
from backend.worker.metrics import GoogleCloudMonitoringMetricSink
from backend.webapp.api_v1.schemas.reporting import (
    IncidentSnapshotV1,
    ReportContentV1,
)


logger = logging.getLogger(__name__)
_TASK_NAME = re.compile(
    r"^ai-job-(?P<job_id>[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12})$",
    re.IGNORECASE,
)
_QUEUE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
_SAFE_TERMINAL_CODES = frozenset(
    {
        "job_output_invalid",
        "job_target_invalid",
        "job_result_conflict",
        "job_authorization_invalid",
        "job_result_contract_unavailable",
    }
)
_REPORT_KEYS = {
    "first_person": ReportType.FIRST_PERSON,
    "supervisor_summary": ReportType.SUPERVISOR_SUMMARY,
    "cover_letter": ReportType.COVER_LETTER,
    "disciplinary": ReportType.DISCIPLINARY,
    "investigation": ReportType.INVESTIGATION,
    "form_005": ReportType.FORM_005,
}
_PLACEHOLDER = re.compile(r"^\s*\[Error generating\b", re.IGNORECASE)
_MAX_RESULT_REPORTS = 20


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
    """Validated content returned by an injected or route-neutral engine."""

    report_content: ReportContentV1 | None = None
    incident_content: IncidentSnapshotV1 | None = None
    report_contents: dict[str, ReportContentV1] = field(default_factory=dict)


class ReportEngine(Protocol):
    def run(self, session, job: AiJob) -> object: ...


class RouteNeutralReportEngine:
    """Call the RP-03 adapters without adding another report pipeline."""

    @staticmethod
    def _generation_payload(session, job: AiJob, incident: Incident) -> dict:
        payload = {
            "notes": incident.field_notes,
            "category": incident.category or "",
            "slots": incident.extracted_facts,
            "answers": incident.gap_answers,
            "charges": incident.charges,
        }
        if job.job_type == "disciplinary":
            report = session.get(Report, job.report_id) if job.report_id else None
            owner_id = report.reporting_staff_member_id if report else None
            first_person = None
            if report is not None and report.report_type == ReportType.FIRST_PERSON:
                first_person = report
            elif owner_id is not None:
                first_person = session.scalar(
                    select(Report).where(
                        Report.incident_id == incident.id,
                        Report.report_type == ReportType.FIRST_PERSON,
                        Report.reporting_staff_member_id == owner_id,
                    )
                )
            else:
                first_person = session.scalar(
                    select(Report)
                    .where(
                        Report.incident_id == incident.id,
                        Report.report_type == ReportType.FIRST_PERSON,
                    )
                    .order_by(Report.id)
                    .limit(1)
                )
            payload["reports"] = {
                "first_person": str(
                    (first_person.current_content if first_person else {}).get(
                        "narrative",
                        "",
                    )
                ),
            }
        return payload

    def run(self, session, job: AiJob) -> object:
        incident = session.get(Incident, job.incident_id)
        if incident is None:
            raise TerminalJobFailure("job_target_invalid")
        if job.job_type == "classify":
            return report_service.classify_incident_notes(incident.field_notes)
        provider = SqlStaffProvider(session)
        if job.job_type == "extract":
            category = incident.category or str(
                (incident.classification or {}).get("incident_type", "")
            )
            if not category:
                raise TerminalJobFailure("job_output_invalid")
            return report_service.extract_incident_notes(
                incident.field_notes,
                category,
                provider,
            )
        payload = self._generation_payload(session, job, incident)
        if job.job_type == "generate":
            return report_service.generate_report_set(
                payload,
                staff_provider=provider,
            )
        if job.job_type == "disciplinary":
            return report_service.generate_disciplinary_report(
                payload,
                staff_provider=provider,
            )
        raise TerminalJobFailure("job_output_invalid")


def _incident_payload(incident: Incident) -> dict[str, object]:
    return {
        "schema_version": 1,
        "field_notes": incident.field_notes,
        "incident_date": incident.incident_date,
        "incident_time": incident.incident_time,
        "facility": incident.facility,
        "shift": incident.shift,
        "location": incident.location,
        "category": incident.category,
        "classification": incident.classification,
        "extracted_facts": incident.extracted_facts,
        "gap_answers": incident.gap_answers,
        "charges": incident.charges,
        "validation": incident.validation,
        "warnings": [],
    }


def _normalize_engine_result(
    job: AiJob,
    incident: Incident,
    raw: object,
) -> JobEngineResult:
    if isinstance(raw, JobEngineResult):
        return raw
    if type(raw) is not dict:
        raise TerminalJobFailure("job_output_invalid")

    if job.job_type == "classify":
        incident_type = raw.get("incident_type")
        charges = raw.get("charges", [])
        if (
            not isinstance(incident_type, str)
            or not incident_type.strip()
            or type(charges) is not list
            or any(not isinstance(value, str) for value in charges)
        ):
            raise TerminalJobFailure("job_output_invalid")
        payload = _incident_payload(incident)
        payload.update(
            {
                "category": incident_type,
                "classification": dict(raw),
                "charges": charges,
            }
        )
        return JobEngineResult(
            incident_content=IncidentSnapshotV1.model_validate(payload),
        )

    if job.job_type == "extract":
        slots = raw.get("slots")
        if type(slots) is not dict:
            raise TerminalJobFailure("job_output_invalid")
        validation = {
            key: raw[key]
            for key in ("gaps", "blocking_remaining", "checklist", "auto_content")
            if key in raw
        }
        payload = _incident_payload(incident)
        payload.update(
            {
                "extracted_facts": slots,
                "validation": validation,
                "warnings": [str(value)[:200] for value in raw.get("markers", [])[:100]]
                if isinstance(raw.get("markers", []), list)
                else [],
            }
        )
        return JobEngineResult(
            incident_content=IncidentSnapshotV1.model_validate(payload),
        )

    errors: list[object] = []
    for candidate in (raw.get("generation_errors"), raw.get("_errors")):
        if isinstance(candidate, list):
            errors.extend(candidate)
    reports = raw.get("reports")
    if type(reports) is not dict:
        raise TerminalJobFailure("job_output_invalid")
    nested_errors = reports.get("_errors")
    if isinstance(nested_errors, list):
        errors.extend(nested_errors)
    if errors:
        # Adapter generation errors represent exhausted provider attempts. The
        # placeholder text accompanying them is never a successful result.
        raise TransientJobFailure("report generation dependency unavailable")

    selected = reports
    if job.job_type == "disciplinary":
        selected = {"disciplinary": reports.get("disciplinary")}
    report_contents: dict[str, ReportContentV1] = {}
    raw_markers = raw.get("markers", [])
    warnings = (
        [str(value)[:200] for value in raw_markers[:100]]
        if isinstance(raw_markers, list)
        else []
    )
    validation = {key: raw[key] for key in ("style", "flags", "repaired") if key in raw}
    for key, narrative in selected.items():
        if key not in _REPORT_KEYS:
            continue
        if (
            not isinstance(narrative, str)
            or not narrative.strip()
            or _PLACEHOLDER.match(narrative)
        ):
            raise TerminalJobFailure("job_output_invalid")
        report_contents[key] = ReportContentV1(
            narrative=narrative,
            validation=validation,
            warnings=warnings,
        )
    form005 = raw.get("form005")
    if job.job_type == "generate" and isinstance(form005, dict) and form005:
        narrative = form005.get("narrative") or reports.get("first_person")
        editable_fields = {
            str(key): value
            for key, value in form005.items()
            if isinstance(key, str)
            and isinstance(value, (str, int, float, bool, type(None)))
        }
        if not isinstance(narrative, str) or not narrative.strip():
            raise TerminalJobFailure("job_output_invalid")
        report_contents["form_005"] = ReportContentV1(
            narrative=narrative,
            editable_fields=editable_fields,
            validation=validation,
            warnings=warnings,
        )
    if not report_contents:
        raise TerminalJobFailure("job_output_invalid")
    return JobEngineResult(report_contents=report_contents)


class JobProcessor:
    def __init__(
        self,
        *,
        session_factory=None,
        report_engine=None,
        metric_sink=None,
        now=None,
    ):
        self._session_factory = session_factory or session_scope
        self._engine = report_engine or RouteNeutralReportEngine()
        self._metric_sink = metric_sink or GoogleCloudMonitoringMetricSink(
            project_id=os.environ.get("GCP_PROJECT_ID", ""),
        )
        self._now = now or (lambda: datetime.now(UTC))

    def _scope(self):
        begin = getattr(self._session_factory, "begin", None)
        return begin() if callable(begin) else self._session_factory()

    @staticmethod
    def _actor(session, job: AiJob) -> Actor:
        account = session.get(Account, job.requested_by_account_id)
        staff = session.get(StaffMember, account.staff_member_id) if account else None
        if (
            account is None
            or account.status != "active"
            or staff is None
            or not staff.is_active
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
    def _authorize_report_target(
        session,
        job: AiJob,
        actor: Actor,
    ) -> Report | None:
        if job.report_id is None:
            return None
        report = session.scalar(
            select(Report).where(Report.id == job.report_id).with_for_update()
        )
        if report is None or report.incident_id != job.incident_id:
            raise TerminalJobFailure("job_target_invalid")
        access = session.scalar(
            select(ReportAccess)
            .where(
                ReportAccess.report_id == report.id,
                ReportAccess.staff_member_id == actor.staff_member_id,
                ReportAccess.revoked_at.is_(None),
            )
            .with_for_update()
        )
        if access is None:
            raise TerminalJobFailure("job_authorization_invalid")
        return report

    @staticmethod
    def _source_revision(session, job: AiJob) -> IncidentRevision:
        revision = session.scalar(
            select(IncidentRevision).where(
                IncidentRevision.incident_id == job.incident_id,
                IncidentRevision.revision_number == job.base_incident_revision,
            )
        )
        if revision is None:
            raise TerminalJobFailure("job_target_invalid")
        return revision

    @staticmethod
    def _reporting_staff_ids(
        session,
        incident: Incident,
        revision: IncidentRevision,
    ) -> tuple[UUID, ...]:
        snapshot = revision.snapshot if isinstance(revision.snapshot, dict) else {}
        metadata = snapshot.get("server_metadata")
        raw_ids = (
            metadata.get("reporting_staff_ids") if isinstance(metadata, dict) else None
        )
        if not isinstance(raw_ids, list) or not 1 <= len(raw_ids) <= 20:
            raise TerminalJobFailure("job_target_invalid")
        try:
            staff_ids = tuple(dict.fromkeys(UUID(str(value)) for value in raw_ids))
        except (TypeError, ValueError):
            raise TerminalJobFailure("job_target_invalid") from None
        if len(staff_ids) != len(raw_ids):
            raise TerminalJobFailure("job_target_invalid")
        active = set(
            session.scalars(
                select(StaffMember.id).where(
                    StaffMember.id.in_(staff_ids),
                    StaffMember.is_active.is_(True),
                )
            ).all()
        )
        if active != set(staff_ids):
            raise TerminalJobFailure("job_target_invalid")
        return staff_ids

    @staticmethod
    def _authorize_incident_target(
        session,
        *,
        incident: Incident,
        source: IncidentRevision,
        actor: Actor,
    ) -> None:
        if actor.staff_member_id == incident.created_by_staff_member_id:
            return
        snapshot = source.snapshot if isinstance(source.snapshot, dict) else {}
        metadata = snapshot.get("server_metadata")
        raw_ids = (
            metadata.get("reporting_staff_ids") if isinstance(metadata, dict) else []
        )
        try:
            selected = {UUID(str(value)) for value in raw_ids}
        except (TypeError, ValueError):
            selected = set()
        if actor.staff_member_id in selected:
            return
        live_access = session.scalar(
            select(ReportAccess)
            .join(Report, Report.id == ReportAccess.report_id)
            .where(
                Report.incident_id == incident.id,
                ReportAccess.staff_member_id == actor.staff_member_id,
                ReportAccess.revoked_at.is_(None),
            )
            .with_for_update(of=ReportAccess)
            .limit(1)
        )
        if live_access is None:
            raise TerminalJobFailure("job_authorization_invalid")

    @staticmethod
    def _metadata(job: AiJob) -> dict[str, object]:
        return (
            dict(job.request_metadata) if isinstance(job.request_metadata, dict) else {}
        )

    @staticmethod
    def _finish_provider_metadata(job: AiJob) -> None:
        metadata = JobProcessor._metadata(job)
        started = metadata.pop("provider_attempt_started", None)
        if isinstance(started, dict):
            metadata["provider_attempt_completed"] = {"attempt": job.attempts}
        job.request_metadata = metadata

    def _emit_repeat_risk(self, job_type: str) -> None:
        labels = {"job_type": job_type}
        try:
            self._metric_sink.increment(
                "ai_provider_repeat_risk_total",
                labels=labels,
            )
        except Exception:
            # A telemetry outage must not repeat the provider call or alter the
            # already-durable recovery decision. Do not expose raw exceptions.
            logger.error(
                "ai_provider_repeat_risk_metric_emit_failed",
                extra={"event_name": "ai_provider_repeat_risk_metric_emit_failed"},
            )

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
            self._finish_provider_metadata(job)
            job.state = "failed"
            job.stage = "failed"
            job.error_code = code
            job.completed_at = fixed
            job.claim_token = None
            job.lease_expires_at = None
            PostgresAuditWriter().append(
                session,
                AuditEventInput(
                    actor_account_id=account.id,
                    actor_staff_member_id=account.staff_member_id,
                    action="ai.job_failed",
                    result="failed",
                    request_id=f"job_{job.id}",
                    target_type="ai_job",
                    target_id=job.id,
                    details={
                        "job_id": str(job.id),
                        "job_type": job.job_type,
                        "result_code": code,
                    },
                    client_version="0.0.0-worker",
                ),
            )

    def _release_transient(self, job_id: UUID, claim_token: UUID) -> None:
        with self._scope() as session:
            job = session.scalar(
                select(AiJob).where(AiJob.id == job_id).with_for_update()
            )
            if job is None or job.state in TERMINAL_STATES:
                return
            if job.state == "running" and job.claim_token == claim_token:
                # Retain provider_attempt_started. A later claim consumes it
                # and produces the one bounded repeat-risk event.
                job.state = "queued"
                job.stage = "queued"
                job.claim_token = None
                job.lease_expires_at = None

    def _claim(self, job_id: UUID) -> tuple[UUID | None, str | None]:
        fixed = self._now()
        repeat_job_type = None
        with self._scope() as session:
            claimed = claim_job(session, job_id, now=fixed)
            if claimed is None:
                existing = session.get(AiJob, job_id)
                if existing is not None and existing.state == "running":
                    raise TransientJobFailure("job lease is active")
                return None, None
            claim_token = claimed.claim_token
            metadata = self._metadata(claimed)
            previous = metadata.pop("provider_attempt_started", None)
            if isinstance(previous, dict) and previous.get("claim_token") != str(
                claim_token
            ):
                repeat_job_type = claimed.job_type
                metadata["provider_repeat_risk_emitted_attempt"] = claimed.attempts
            claimed.request_metadata = metadata
        if claim_token is None:
            raise TransientJobFailure("job claim is unavailable")
        if repeat_job_type is not None:
            self._emit_repeat_risk(repeat_job_type)
        return claim_token, repeat_job_type

    def _preflight(
        self,
        job_id: UUID,
        claim_token: UUID,
    ) -> None:
        fixed = self._now()
        with self._scope() as session:
            job = session.scalar(
                select(AiJob).where(AiJob.id == job_id).with_for_update()
            )
            if (
                job is None
                or job.state != "running"
                or job.claim_token != claim_token
                or job.lease_expires_at is None
                or job.lease_expires_at <= fixed
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
                self._finish_provider_metadata(job)
                apply_job_result(
                    session,
                    job.id,
                    job.base_incident_revision,
                    claim_token=claim_token,
                    result_reference={},
                    now=fixed,
                    request_id=f"job_{job.id}",
                )
                return
            source = self._source_revision(session, job)
            self._authorize_incident_target(
                session,
                incident=incident,
                source=source,
                actor=actor,
            )
            metadata = self._metadata(job)
            metadata["source_incident_revision_id"] = str(source.id)
            bases: dict[str, int] = {}
            if report is not None:
                bases[str(report.id)] = report.current_revision_number
            elif job.job_type in {"generate", "disciplinary"}:
                staff_ids = self._reporting_staff_ids(session, incident, source)
                if (
                    actor.staff_member_id not in staff_ids
                    and actor.staff_member_id != incident.created_by_staff_member_id
                ):
                    raise TerminalJobFailure("job_authorization_invalid")
                existing = session.scalars(
                    select(Report)
                    .where(
                        Report.incident_id == incident.id,
                        Report.reporting_staff_member_id.in_(staff_ids),
                    )
                    .order_by(Report.id)
                    .limit(_MAX_RESULT_REPORTS + 1)
                ).all()
                if len(existing) > _MAX_RESULT_REPORTS:
                    raise TerminalJobFailure("job_output_invalid")
                bases = {str(row.id): row.current_revision_number for row in existing}
            metadata["target_report_base_revisions"] = bases
            job.request_metadata = metadata
            if job.job_type == "generate":
                job.stage = "generating"

    def _mark_provider_started(self, job_id: UUID, claim_token: UUID) -> None:
        fixed = self._now()
        with self._scope() as session:
            job = session.scalar(
                select(AiJob).where(AiJob.id == job_id).with_for_update()
            )
            if (
                job is None
                or job.state != "running"
                or job.claim_token != claim_token
                or job.lease_expires_at is None
                or job.lease_expires_at <= fixed
            ):
                raise StaleJobClaim("job claim is no longer current")
            metadata = self._metadata(job)
            metadata["provider_attempt_started"] = {
                "attempt": job.attempts,
                "claim_token": str(claim_token),
            }
            job.request_metadata = metadata

    def _call_engine(self, job_id: UUID, claim_token: UUID) -> JobEngineResult:
        with self._scope() as session:
            job = session.get(AiJob, job_id)
            if job is None or job.state != "running" or job.claim_token != claim_token:
                raise StaleJobClaim("job claim is no longer current")
            incident = session.get(Incident, job.incident_id)
            if incident is None:
                raise TerminalJobFailure("job_target_invalid")
            raw = self._engine.run(session, job)
            return _normalize_engine_result(job, incident, raw)

    @staticmethod
    def _attach_sources(
        session,
        *,
        job_id: UUID,
        source_revision_id: UUID,
    ):
        def attach(_session, _context, _instances):
            for pending in _session.new:
                if (
                    isinstance(pending, ReportRevision)
                    and pending.reason == "ai_result"
                ):
                    pending.source_incident_revision_id = source_revision_id
                    pending.source_ai_job_id = job_id

        event.listen(session, "before_flush", attach)
        return attach

    @staticmethod
    def _new_report_shell(
        session,
        *,
        incident: Incident,
        report_type: ReportType,
        owner_staff_id: UUID,
        actor: Actor,
        now: datetime,
    ) -> Report:
        report = Report(
            incident_id=incident.id,
            report_type=report_type,
            reporting_staff_member_id=owner_staff_id,
            prepared_by_staff_member_id=actor.staff_member_id,
            created_by_account_id=actor.account_id,
            status="in_progress",
            current_revision_number=0,
            current_content={},
            created_at=now,
            updated_at=now,
        )
        session.add(report)
        session.flush()
        relationships = [(owner_staff_id, "owner")]
        if actor.staff_member_id != owner_staff_id:
            relationships.append((actor.staff_member_id, "preparer"))
        session.add_all(
            [
                ReportAccess(
                    report_id=report.id,
                    staff_member_id=staff_id,
                    relationship=relationship,
                    granted_by_account_id=actor.account_id,
                    created_at=now,
                )
                for staff_id, relationship in relationships
            ]
        )
        session.flush()
        return report

    def _apply_report_results(
        self,
        session,
        *,
        job: AiJob,
        actor: Actor,
        incident: Incident,
        source: IncidentRevision,
        result: JobEngineResult,
        now: datetime,
    ) -> list[dict[str, object]]:
        metadata = self._metadata(job)
        raw_bases = metadata.get("target_report_base_revisions", {})
        bases = (
            {
                str(key): value
                for key, value in raw_bases.items()
                if isinstance(key, str) and type(value) is int
            }
            if isinstance(raw_bases, dict)
            else {}
        )

        contents = dict(result.report_contents)
        if result.report_content is not None:
            if job.report_id is None:
                raise TerminalJobFailure("job_target_invalid")
            report = session.get(Report, job.report_id)
            if report is None:
                raise TerminalJobFailure("job_target_invalid")
            report_type = getattr(report.report_type, "value", report.report_type)
            contents = {str(report_type): result.report_content}
        if not contents:
            raise TerminalJobFailure("job_output_invalid")

        targets: list[tuple[Report, ReportContentV1, int]] = []
        if job.report_id is not None:
            report = self._authorize_report_target(session, job, actor)
            if report is None:
                raise TerminalJobFailure("job_target_invalid")
            key = str(getattr(report.report_type, "value", report.report_type))
            content = contents.get(key)
            base = bases.get(str(report.id))
            if content is None or type(base) is not int:
                raise TerminalJobFailure("job_output_invalid")
            targets.append((report, content, base))
        else:
            staff_ids = self._reporting_staff_ids(session, incident, source)
            if len(staff_ids) * len(contents) > _MAX_RESULT_REPORTS:
                raise TerminalJobFailure("job_output_invalid")
            for key, content in sorted(contents.items()):
                report_type = _REPORT_KEYS.get(key)
                if report_type is None:
                    raise TerminalJobFailure("job_output_invalid")
                for owner_id in staff_ids:
                    report = session.scalar(
                        select(Report)
                        .where(
                            Report.incident_id == incident.id,
                            Report.report_type == report_type,
                            Report.reporting_staff_member_id == owner_id,
                        )
                        .with_for_update()
                    )
                    if report is None:
                        report = self._new_report_shell(
                            session,
                            incident=incident,
                            report_type=report_type,
                            owner_staff_id=owner_id,
                            actor=actor,
                            now=now,
                        )
                        base = 0
                    else:
                        base = bases.get(str(report.id))
                        if type(base) is not int:
                            raise TerminalJobFailure("job_result_conflict")
                        access = session.scalar(
                            select(ReportAccess)
                            .where(
                                ReportAccess.report_id == report.id,
                                ReportAccess.staff_member_id == actor.staff_member_id,
                                ReportAccess.revoked_at.is_(None),
                            )
                            .with_for_update()
                        )
                        if access is None:
                            raise TerminalJobFailure("job_authorization_invalid")
                    targets.append((report, content, base))

        attach = self._attach_sources(
            session,
            job_id=job.id,
            source_revision_id=source.id,
        )
        references = []
        try:
            for report, content, base in sorted(targets, key=lambda value: value[0].id):
                revision = save_report(
                    session,
                    actor,
                    report.id,
                    content,
                    base,
                    "ai_result",
                    request_id=f"job_{job.id}",
                    client_version="0.0.0-worker",
                )
                references.append(
                    {
                        "report_id": str(report.id),
                        "revision_number": revision.revision_number,
                    }
                )
                for name in (
                    "fast_model",
                    "pro_model",
                    "model_location",
                    "classification_prompt_sha256",
                    "generation_prompt_sha256",
                ):
                    setattr(job, name, getattr(revision, name))
        finally:
            event.remove(session, "before_flush", attach)
        return references

    def _apply(self, job_id: UUID, claim_token: UUID, result: JobEngineResult) -> None:
        completed_at = self._now()
        with self._scope() as session:
            job = session.scalar(
                select(AiJob).where(AiJob.id == job_id).with_for_update()
            )
            if (
                job is None
                or job.state != "running"
                or job.claim_token != claim_token
                or job.lease_expires_at is None
                or job.lease_expires_at <= completed_at
            ):
                raise StaleJobClaim("job claim is no longer current")
            actor = self._actor(session, job)
            incident = session.scalar(
                select(Incident).where(Incident.id == job.incident_id).with_for_update()
            )
            if incident is None:
                raise TerminalJobFailure("job_target_invalid")
            if incident.current_revision_number != job.base_incident_revision:
                self._finish_provider_metadata(job)
                apply_job_result(
                    session,
                    job.id,
                    job.base_incident_revision,
                    claim_token=claim_token,
                    result_reference={},
                    now=completed_at,
                    request_id=f"job_{job.id}",
                )
                return
            source = self._source_revision(session, job)
            self._authorize_incident_target(
                session,
                incident=incident,
                source=source,
                actor=actor,
            )

            if result.incident_content is not None:
                self._finish_provider_metadata(job)
                # The RP-06 success service verifies the unchanged incident
                # base. Complete it first, then append the AI incident result
                # in the same transaction and attach the known revision ref.
                # Any save failure rolls the whole transaction back.
                apply_job_result(
                    session,
                    job.id,
                    job.base_incident_revision,
                    claim_token=claim_token,
                    result_reference={},
                    now=completed_at,
                    request_id=f"job_{job.id}",
                )
                revision = save_incident(
                    session,
                    actor,
                    incident.id,
                    result.incident_content,
                    job.base_incident_revision,
                    "ai_result",
                    request_id=f"job_{job.id}",
                    client_version="0.0.0-worker",
                )
                job.result_reference = {
                    "incident_revision_number": revision.revision_number,
                }
                return

            try:
                references = self._apply_report_results(
                    session,
                    job=job,
                    actor=actor,
                    incident=incident,
                    source=source,
                    result=result,
                    now=completed_at,
                )
            except RevisionConflict:
                # RevisionConflict is a frozen dataclass exception. Catch it
                # before SQLAlchemy's context manager attempts to attach a
                # traceback during rollback on Python 3.14.
                raise TerminalJobFailure("job_result_conflict") from None
            self._finish_provider_metadata(job)
            apply_job_result(
                session,
                job.id,
                job.base_incident_revision,
                claim_token=claim_token,
                result_reference={"reports": references},
                now=completed_at,
                request_id=f"job_{job.id}",
            )

    def run(self, job_id: UUID, *, retry_count: int) -> None:
        del retry_count  # Delivery count is validated but never used as truth.
        claim_token, _repeat = self._claim(job_id)
        if claim_token is None:
            return
        try:
            self._preflight(job_id, claim_token)
            with self._scope() as session:
                current = session.get(AiJob, job_id)
                if current is None or current.state in TERMINAL_STATES:
                    return
            self._mark_provider_started(job_id, claim_token)
            result = self._call_engine(job_id, claim_token)
            self._apply(job_id, claim_token, result)
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
        except TransientJobFailure:
            self._release_transient(job_id, claim_token)
            raise
        except Exception:
            self._release_transient(job_id, claim_token)
            raise TransientJobFailure("worker dependency unavailable") from None


def _delivery_metadata(
    job_id: UUID,
    *,
    expected_queue: str,
) -> tuple[bool, int]:
    task_name = request.headers.get("X-CloudTasks-TaskName", "")
    queue_name = request.headers.get("X-CloudTasks-QueueName", "")
    retry_value = request.headers.get("X-CloudTasks-TaskRetryCount", "")
    if not task_name or not queue_name or retry_value == "":
        return False, 0
    match = _TASK_NAME.fullmatch(task_name)
    if (
        match is None
        or match.group("job_id").lower() != str(job_id)
        or not _QUEUE_NAME.fullmatch(queue_name)
        or queue_name != expected_queue
    ):
        return False, 0
    try:
        retry_count = int(retry_value)
    except ValueError:
        return False, 0
    if not 0 <= retry_count <= 100:
        return False, 0
    return True, retry_count


def create_worker_blueprint(processor, *, queue_name: str) -> Blueprint:
    if not _QUEUE_NAME.fullmatch(queue_name):
        raise ValueError("Cloud Tasks worker queue configuration is invalid")
    blueprint = Blueprint("private_worker", __name__)

    @blueprint.post("/internal/jobs/<uuid:job_id>/run")
    def run_job(job_id: UUID):
        metadata_present = all(
            header in request.headers
            for header in (
                "X-CloudTasks-TaskName",
                "X-CloudTasks-QueueName",
                "X-CloudTasks-TaskRetryCount",
            )
        )
        valid_metadata, retry_count = _delivery_metadata(
            job_id,
            expected_queue=queue_name,
        )
        if not metadata_present:
            return jsonify({"error": "cloud_tasks_metadata_required"}), 401
        payload = request.get_json(silent=True)
        if (
            not valid_metadata
            or type(payload) is not dict
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
    "JobEngineResult",
    "JobProcessor",
    "TerminalJobFailure",
    "TransientJobFailure",
    "create_worker_blueprint",
]
