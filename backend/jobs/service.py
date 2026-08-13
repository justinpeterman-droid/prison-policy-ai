"""Durable, idempotent AI job submission, claiming, and result application.

`submit_job()` runs everything -- actor/incident/base-revision authorization,
the ID-06 idempotency claim, the queued `AiJob` row, its `TaskOutbox` row,
and a safe `ai.job_submitted` audit event -- in the caller's single
transaction, mirroring `backend.reports.persistence`'s pattern: a failure
partway through leaves the whole thing rolled back, never an orphan job,
outbox row, idempotency record, or audit fragment.

`claim_job()` and `apply_job_result()` are consumed by RP-07's dispatcher and
worker; they exist here because the durability guarantees they provide --
`FOR UPDATE SKIP LOCKED` claiming and stale-incident-revision rejection --
are part of this task's contract, not the dispatcher's.

Nothing in this module calls the report engine, Vertex AI, or Cloud Tasks.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.identity.audit import AuditEventInput, AuditWriter, PostgresAuditWriter
from backend.identity.idempotency import claim_idempotency, complete_idempotency, request_digest
from backend.jobs.outbox import claim_outbox_row, create_outbox_row, mark_outbox_dispatched, mark_outbox_terminal
from backend.persistence.models.jobs import AI_JOB_TYPES, AiJob, TaskOutbox
from backend.persistence.models.reporting import Incident
from backend.reports.persistence import IncidentNotFound, get_incident
from backend.reports.revisions import RevisionConflict

# `Actor` is used only for type hints here, deferred to TYPE_CHECKING: it
# lives in `backend.webapp.api_v1.middleware`, a submodule of the
# `backend.webapp.api_v1` package, and this module (via `reports.persistence`/
# `reports.revisions`, imported above) already sits on that package's
# existing import chain. A real module-scope import here would be circular
# whenever this module is the first thing to touch that package tree, as a
# standalone unit test does; see `backend/webapp/api_v1/jobs.py` for the
# matching lazy import that keeps the route layer out of this module's own
# import chain.
if TYPE_CHECKING:
    from backend.webapp.api_v1.middleware import Actor


__all__ = [
    "JOB_STAGE_BY_TYPE",
    "JOB_TYPES",
    "TERMINAL_JOB_STATES",
    "JobNotFound",
    "JobResultConflict",
    "SubmitJobCommand",
    "apply_job_result",
    "claim_job",
    "get_job",
    "submit_job",
]

#: The four approved AI job types; mirrors backend.persistence.models.jobs.AI_JOB_TYPES.
JOB_TYPES = frozenset(AI_JOB_TYPES)
#: The stage a claimed job advances to, keyed by job_type.
JOB_STAGE_BY_TYPE = {
    "classify": "classifying",
    "extract": "extracting",
    "generate": "generating",
    "disciplinary": "disciplinary",
}
TERMINAL_JOB_STATES = frozenset({"succeeded", "failed", "cancelled"})


class JobNotFound(LookupError):
    """No job exists, or the requesting actor cannot see it."""


@dataclass(frozen=True)
class JobResultConflict(Exception):
    """The incident moved since the job was queued; the result is stale."""

    job_id: UUID
    current_incident_revision_number: int

    def __str__(self) -> str:
        return (
            "the incident changed since the job was queued; current revision is "
            f"{self.current_incident_revision_number}"
        )


@dataclass(frozen=True)
class SubmitJobCommand:
    incident_id: UUID
    job_type: str


def _canonical_request(incident_id: UUID, job_type: str, base_revision_number: int) -> dict:
    """The exact payload whose SHA-256 digest is claimed for idempotency.

    Pure and side-effect free so tests can exercise digest canonicalization
    (same payload -> same digest, any field changing -> a different digest)
    without a database.
    """
    return {
        "incident_id": str(incident_id),
        "job_type": job_type,
        "base_revision_number": base_revision_number,
    }


def _job_reference(job: AiJob) -> dict[str, object]:
    return {"job_id": str(job.id)}


def _job_from_reference(session: Session, actor: Actor, reference: dict) -> AiJob:
    try:
        job_id = UUID(str(reference["job_id"]))
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("idempotency reference is invalid") from None
    job = session.get(AiJob, job_id)
    if job is None:
        raise RuntimeError("idempotency reference is invalid")
    try:
        get_incident(session, actor, job.incident_id)
    except IncidentNotFound:
        raise RuntimeError("idempotency reference is invalid") from None
    return job


def get_job(session: Session, actor: Actor, job_id: UUID) -> AiJob:
    """Load a job for its requesting actor (with live incident access) or an Admin."""
    job = session.get(AiJob, job_id)
    if job is None:
        raise JobNotFound("Job not found.")
    if actor.role != "admin":
        try:
            get_incident(session, actor, job.incident_id)
        except IncidentNotFound:
            raise JobNotFound("Job not found.") from None
    return job


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
    """Authorize, claim idempotency, queue the job, and audit -- one transaction.

    Same idempotency key with the same payload replays the original queued
    job (202). Same key with a changed payload raises `IdempotencyConflict`
    (409 idempotency_conflict). A stale `base_revision_number` raises
    `RevisionConflict` (409 revision_conflict). Every raise here happens
    before anything is committed by the caller, so a failure leaves no
    orphan job, outbox row, idempotency record, or audit event.
    """
    if command.job_type not in JOB_TYPES:
        raise ValueError("job type is invalid")
    if (
        not isinstance(base_revision_number, int)
        or isinstance(base_revision_number, bool)
        or base_revision_number < 0
    ):
        raise ValueError("base_revision_number must be a nonnegative integer")
    fixed = now or datetime.now(UTC)
    digest = request_digest(
        _canonical_request(command.incident_id, command.job_type, base_revision_number))
    claim = claim_idempotency(
        session, actor, key=idempotency_key, action=f"ai_job.{command.job_type}",
        request_sha256=digest, now=fixed,
    )
    if claim.replayed:
        return _job_from_reference(session, actor, claim.response_reference or {})

    # Authorization precedes any write: an actor without live incident access
    # never causes a job/outbox/audit row to exist, even transiently.
    get_incident(session, actor, command.incident_id)
    incident = session.scalar(
        select(Incident).where(Incident.id == command.incident_id).with_for_update()
    )
    if incident is None:
        raise IncidentNotFound("Incident not found.")
    if incident.current_revision_number != base_revision_number:
        raise RevisionConflict(
            current_revision_number=incident.current_revision_number,
            status=incident.status,
            updated_at=incident.updated_at,
        )

    job = AiJob(
        id=uuid4(),
        incident_id=incident.id,
        report_id=None,
        requested_by_account_id=actor.account_id,
        job_type=command.job_type,
        state="queued",
        stage="queued",
        idempotency_key=idempotency_key,
        request_sha256=digest,
        attempt_count=0,
        request={"base_revision_number": base_revision_number},
        result={},
        expected_incident_revision_number=base_revision_number,
        created_at=fixed,
    )
    session.add(job)
    session.flush()
    create_outbox_row(session, job.id, now=fixed)

    writer = audit_writer or PostgresAuditWriter()
    writer.append(session, AuditEventInput(
        actor_account_id=actor.account_id,
        actor_staff_member_id=actor.staff_member_id,
        action="ai.job_submitted",
        result="success",
        request_id=request_id,
        target_type="ai_job",
        target_id=job.id,
        details={
            "job_id": str(job.id), "job_type": command.job_type,
            "incident_id": str(incident.id),
        },
        client_version=client_version,
    ))
    complete_idempotency(
        session, claim, response_status=202,
        response_reference=_job_reference(job), now=fixed,
    )
    session.flush()
    return job


def claim_job(session: Session, job_id: UUID) -> AiJob | None:
    """Lock and advance one queued job for processing, or return None.

    Uses `FOR UPDATE SKIP LOCKED` on the job's outbox row, so concurrent
    claimers never double-process the same job -- a contender simply
    receives `None` rather than blocking or racing.
    """
    outbox = claim_outbox_row(session, job_id)
    if outbox is None:
        return None
    job = session.scalar(select(AiJob).where(AiJob.id == job_id).with_for_update())
    if job is None:
        return None
    now = datetime.now(UTC)
    if job.state == "queued":
        job.state = "running"
        job.started_at = job.started_at or now
    job.stage = JOB_STAGE_BY_TYPE.get(job.job_type, job.stage)
    job.attempt_count += 1
    mark_outbox_dispatched(outbox, now=now)
    session.flush()
    return job


def apply_job_result(
    session: Session, job_id: UUID, expected_incident_revision: int,
) -> None:
    """Durably mark a claimed job's result applied, guarding against staleness.

    Idempotent: a job already in a terminal state (`succeeded`, `failed`, or
    `cancelled`) is left untouched -- a redelivered/duplicate Cloud Tasks
    delivery of an already-applied result is a safe no-op, never a second
    application. A stale `expected_incident_revision` (the incident moved
    since the job was queued) marks the job terminally `failed` with
    `job_result_conflict` and raises `JobResultConflict` rather than letting
    the caller overwrite newer incident/report content.
    """
    job = session.scalar(select(AiJob).where(AiJob.id == job_id).with_for_update())
    if job is None:
        raise JobNotFound("Job not found.")
    if job.state in TERMINAL_JOB_STATES:
        return
    current_revision = session.scalar(
        select(Incident.current_revision_number).where(Incident.id == job.incident_id)
    )
    if current_revision is None:
        raise JobNotFound("Job not found.")
    now = datetime.now(UTC)
    outbox = session.scalar(
        select(TaskOutbox).where(TaskOutbox.ai_job_id == job_id).with_for_update()
    )
    if current_revision != expected_incident_revision:
        job.state = "failed"
        job.stage = "failed"
        job.error_code = "job_result_conflict"
        job.completed_at = now
        if outbox is not None:
            mark_outbox_terminal(outbox, "failed", error_code="job_result_conflict")
        session.flush()
        raise JobResultConflict(job_id, current_revision)
    job.state = "succeeded"
    job.stage = "completed"
    job.completed_at = now
    if outbox is not None:
        mark_outbox_terminal(outbox, "completed")
    session.flush()
