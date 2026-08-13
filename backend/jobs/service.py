"""Durable, idempotent AI-job control services.

The caller owns the transaction. Submission, shared idempotency, the queued
job, its outbox intent, and audit attribution therefore commit or roll back as
one unit. Provider input/output stays in incident/report revision services;
these records contain only bounded control metadata and safe result references.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from backend.identity.audit import AuditEventInput, AuditWriter, PostgresAuditWriter
from backend.identity.idempotency import (
    claim_idempotency,
    complete_idempotency,
    request_digest,
)
from backend.jobs.outbox import enqueue_job
from backend.persistence.models.identity import Account
from backend.persistence.models.jobs import (
    AiJob,
    InvalidJobResultReference,
    normalize_job_result_reference,
)
from backend.persistence.models.reporting import (
    Incident,
    IncidentRevision,
    Report,
    ReportAccess,
    ReportRevision,
)
from backend.reports.persistence import (
    IncidentNotFound,
    get_incident,
)
from backend.reports.revisions import RevisionConflict
from backend.webapp.api_v1.middleware import Actor


JobType = Literal["classify", "extract", "generate", "disciplinary"]
JOB_TYPES = frozenset({"classify", "extract", "generate", "disciplinary"})
CLAIM_STAGES = {
    "classify": "classifying",
    "extract": "extracting",
    "generate": "validating",
    "disciplinary": "disciplinary",
}
TERMINAL_STATES = frozenset({"succeeded", "failed", "cancelled"})
JOB_LEASE_DURATION = timedelta(minutes=20)


class JobNotFound(LookupError):
    """The job is missing or concealed by current authorization."""


class StaleJobClaim(ValueError):
    """The worker no longer owns the durable execution lease."""

    code = "job_claim_expired"


@dataclass(frozen=True)
class SubmitJobCommand:
    incident_id: UUID
    job_type: JobType | str
    report_id: UUID | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.incident_id, UUID):
            raise ValueError("incident ID is invalid")
        if self.job_type not in JOB_TYPES:
            raise ValueError("job type is invalid")
        if self.report_id is not None and not isinstance(self.report_id, UUID):
            raise ValueError("report ID is invalid")

    def canonical_payload(self, *, base_revision_number: int) -> dict[str, object]:
        if (
            not isinstance(base_revision_number, int)
            or isinstance(base_revision_number, bool)
            or base_revision_number < 1
        ):
            raise ValueError("base revision must be a positive integer")
        payload: dict[str, object] = {
            "base_revision_number": base_revision_number,
            "incident_id": str(self.incident_id),
            "job_type": self.job_type,
        }
        if self.report_id is not None:
            payload["report_id"] = str(self.report_id)
        return payload


def _job_from_reference(session: Session, reference: dict | None) -> AiJob:
    try:
        job_id = UUID(str((reference or {})["job_id"]))
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("idempotency response reference is invalid") from None
    job = session.get(AiJob, job_id)
    if job is None:
        raise RuntimeError("idempotency response reference is invalid")
    return job


def _authorize_incident(session: Session, actor: Actor, incident_id: UUID) -> Incident:
    # Lock before the live access query so a report save/transfer cannot race the
    # base-revision decision. Report-access revocation takes the report lock
    # first; this route holds no report lock unless a report is explicitly bound.
    incident = session.scalar(
        select(Incident).where(Incident.id == incident_id).with_for_update()
    )
    if incident is None:
        raise IncidentNotFound("Incident not found.")
    view = get_incident(session, actor, incident_id)
    if (
        actor.staff_member_id != incident.created_by_staff_member_id
        and actor.staff_member_id not in view.reporting_staff_ids
    ):
        # Report access is revocable, so lock and revalidate the live row in
        # this transaction rather than trusting the earlier visibility read.
        live_access = session.scalar(
            select(ReportAccess)
            .join(Report, Report.id == ReportAccess.report_id)
            .where(
                Report.incident_id == incident_id,
                ReportAccess.staff_member_id == actor.staff_member_id,
                ReportAccess.revoked_at.is_(None),
            )
            .with_for_update()
            .limit(1)
        )
        if live_access is None:
            raise IncidentNotFound("Incident not found.")
    return incident


def _authorize_bound_report(
    session: Session, actor: Actor, command: SubmitJobCommand,
) -> None:
    if command.report_id is None:
        return
    report = session.scalar(
        select(Report).where(Report.id == command.report_id).with_for_update()
    )
    if report is None or report.incident_id != command.incident_id:
        raise IncidentNotFound("Incident not found.")
    live_access = session.scalar(
        select(ReportAccess)
        .where(
            ReportAccess.report_id == command.report_id,
            ReportAccess.staff_member_id == actor.staff_member_id,
            ReportAccess.revoked_at.is_(None),
        )
        .with_for_update()
    )
    if live_access is None:
        raise IncidentNotFound("Incident not found.")


def _append_audit(
    session: Session,
    writer: AuditWriter,
    *,
    actor_account_id: UUID,
    actor_staff_member_id: UUID,
    action: str,
    job: AiJob,
    request_id: str,
    client_version: str,
    details: dict[str, object],
) -> None:
    writer.append(session, AuditEventInput(
        actor_account_id=actor_account_id,
        actor_staff_member_id=actor_staff_member_id,
        action=action,
        result="success" if action != "ai.job_failed" else "failed",
        request_id=request_id,
        target_type="ai_job",
        target_id=job.id,
        details=details,
        client_version=client_version,
    ))


def submit_job(
    session: Session,
    actor: Actor,
    command: SubmitJobCommand,
    idempotency_key: str,
    base_revision_number: int,
    *,
    now: datetime | None = None,
    request_id: str,
    client_version: str,
    audit_writer: AuditWriter | None = None,
) -> AiJob:
    """Authorize and add one job/outbox/idempotency/audit atomic unit."""
    canonical = command.canonical_payload(base_revision_number=base_revision_number)
    fixed = now or datetime.now(UTC)
    incident = _authorize_incident(session, actor, command.incident_id)
    _authorize_bound_report(session, actor, command)
    claim = claim_idempotency(
        session,
        actor,
        key=idempotency_key,
        action="ai.job.submit",
        request_sha256=request_digest(canonical),
        now=fixed,
    )
    if claim.replayed:
        return _job_from_reference(session, claim.response_reference)
    if incident.current_revision_number != base_revision_number:
        raise RevisionConflict(
            current_revision_number=incident.current_revision_number,
            status=incident.status,
            updated_at=incident.updated_at,
        )

    job = AiJob(
        id=uuid4(),
        incident_id=command.incident_id,
        report_id=command.report_id,
        requested_by_account_id=actor.account_id,
        job_type=command.job_type,
        state="queued",
        stage="queued",
        idempotency_key=idempotency_key,
        request_sha256=request_digest(canonical),
        base_incident_revision=base_revision_number,
        attempts=0,
        request_metadata={"base_revision_number": base_revision_number},
        result_reference={},
        created_at=fixed,
    )
    session.add(job)
    enqueue_job(session, job.id, now=fixed)
    _append_audit(
        session,
        audit_writer or PostgresAuditWriter(),
        actor_account_id=actor.account_id,
        actor_staff_member_id=actor.staff_member_id,
        action="ai.job_submitted",
        job=job,
        request_id=request_id,
        client_version=client_version,
        details={
            "job_id": str(job.id),
            "job_type": command.job_type,
            "incident_id": str(command.incident_id),
        },
    )
    complete_idempotency(
        session,
        claim,
        response_status=202,
        response_reference={"job_id": str(job.id)},
        now=fixed,
    )
    session.flush()
    return job


def get_job(session: Session, actor: Actor, job_id: UUID) -> AiJob:
    job = session.get(AiJob, job_id)
    if job is None:
        raise JobNotFound("Job not found.")
    if actor.role != "admin" and job.requested_by_account_id != actor.account_id:
        raise JobNotFound("Job not found.")
    try:
        get_incident(session, actor, job.incident_id)
    except IncidentNotFound:
        raise JobNotFound("Job not found.") from None
    return job


def claim_job(
    session: Session, job_id: UUID, *, now: datetime | None = None,
) -> AiJob | None:
    """Claim queued work or safely reclaim a worker whose lease expired."""
    fixed = now or datetime.now(UTC)
    job = session.scalar(
        select(AiJob)
        .where(
            AiJob.id == job_id,
            or_(
                AiJob.state == "queued",
                and_(
                    AiJob.state == "running",
                    or_(
                        AiJob.lease_expires_at.is_(None),
                        AiJob.lease_expires_at <= fixed,
                    ),
                ),
            ),
        )
        .with_for_update(skip_locked=True)
    )
    if job is None:
        return None
    job.state = "running"
    job.stage = CLAIM_STAGES[job.job_type]
    job.attempts += 1
    if job.started_at is None:
        job.started_at = fixed
    job.claim_token = uuid4()
    job.lease_expires_at = fixed + JOB_LEASE_DURATION
    session.flush()
    return job


def _validate_result_targets(
    session: Session, job: AiJob, reference: dict[str, object],
) -> None:
    incident_revision_number = reference.get("incident_revision_number")
    if incident_revision_number is not None:
        incident_revision_id = session.scalar(select(IncidentRevision.id).where(
            IncidentRevision.incident_id == job.incident_id,
            IncidentRevision.revision_number == incident_revision_number,
        ))
        if incident_revision_id is None:
            raise InvalidJobResultReference("job result reference is invalid")

    for item in reference.get("reports", []):
        report_id = UUID(str(item["report_id"]))
        revision_number = int(item["revision_number"])
        report_revision_id = session.scalar(
            select(ReportRevision.id)
            .join(Report, Report.id == ReportRevision.report_id)
            .where(
                ReportRevision.report_id == report_id,
                ReportRevision.revision_number == revision_number,
                Report.incident_id == job.incident_id,
            )
        )
        if report_revision_id is None:
            raise InvalidJobResultReference("job result reference is invalid")


def apply_job_result(
    session: Session,
    job_id: UUID,
    expected_incident_revision: int,
    *,
    claim_token: UUID | None = None,
    result_reference: object | None = None,
    now: datetime | None = None,
    request_id: str | None = None,
    client_version: str = "0.0.0-worker",
    audit_writer: AuditWriter | None = None,
) -> None:
    """Finalize at most once, making a stale base a durable safe failure."""
    if (
        not isinstance(expected_incident_revision, int)
        or isinstance(expected_incident_revision, bool)
        or expected_incident_revision < 1
    ):
        raise ValueError("expected incident revision must be a positive integer")
    safe_reference = normalize_job_result_reference(
        {} if result_reference is None else result_reference,
    )
    fixed = now or datetime.now(UTC)
    job = session.scalar(
        select(AiJob).where(AiJob.id == job_id).with_for_update()
    )
    if job is None:
        raise JobNotFound("Job not found.")
    if job.state in TERMINAL_STATES:
        return
    if job.state != "running":
        raise ValueError("job must be claimed before applying a result")
    if (
        not isinstance(claim_token, UUID)
        or job.claim_token != claim_token
        or job.lease_expires_at is None
        or job.lease_expires_at <= fixed
    ):
        raise StaleJobClaim("job claim is no longer current")
    incident = session.scalar(
        select(Incident).where(Incident.id == job.incident_id).with_for_update()
    )
    if incident is None:
        raise JobNotFound("Job not found.")
    account = session.get(Account, job.requested_by_account_id)
    if account is None:
        raise RuntimeError("job requester attribution is unavailable")
    writer = audit_writer or PostgresAuditWriter()
    audit_request_id = request_id or f"job_{job.id}"
    stale = (
        expected_incident_revision != job.base_incident_revision
        or incident.current_revision_number != expected_incident_revision
    )
    if stale:
        job.state = "failed"
        job.stage = "failed"
        job.error_code = "job_result_conflict"
        job.completed_at = fixed
        job.claim_token = None
        job.lease_expires_at = None
        _append_audit(
            session,
            writer,
            actor_account_id=account.id,
            actor_staff_member_id=account.staff_member_id,
            action="ai.job_failed",
            job=job,
            request_id=audit_request_id,
            client_version=client_version,
            details={
                "job_id": str(job.id),
                "job_type": job.job_type,
                "result_code": "job_result_conflict",
            },
        )
        session.flush()
        return

    _validate_result_targets(session, job, safe_reference)
    job.state = "succeeded"
    job.stage = "completed"
    job.error_code = None
    job.result_reference = safe_reference
    job.completed_at = fixed
    job.claim_token = None
    job.lease_expires_at = None
    latency_ms = max(0, min(int((fixed - job.created_at).total_seconds() * 1000), 1_000_000_000))
    _append_audit(
        session,
        writer,
        actor_account_id=account.id,
        actor_staff_member_id=account.staff_member_id,
        action="ai.job_succeeded",
        job=job,
        request_id=audit_request_id,
        client_version=client_version,
        details={
            "job_id": str(job.id),
            "job_type": job.job_type,
            "latency_ms": latency_ms,
        },
    )
    session.flush()
