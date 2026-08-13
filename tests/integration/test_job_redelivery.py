"""PostgreSQL locking and at-most-once durable AI-job result contracts."""

from datetime import UTC, datetime

from sqlalchemy import func, select

from backend.persistence.models import AuditEvent
from backend.persistence.models.jobs import AiJob
from backend.jobs.service import (
    SubmitJobCommand,
    apply_job_result,
    claim_job,
    submit_job,
)


FIXED_NOW = datetime(2026, 8, 12, 15, 15, tzinfo=UTC)


def _submit(session, actor, incident_id, key):
    job = submit_job(
        session,
        actor,
        SubmitJobCommand(incident_id, "classify"),
        key,
        1,
        now=FIXED_NOW,
        request_id=f"request_{key}",
        client_version="1.0.0",
    )
    session.commit()
    return job.id


def test_claim_job_uses_skip_locked_for_concurrent_delivery(
    db_session, db_session_factory, user_actor, fictional_incident, fictional_report,
):
    db_session.commit()
    with db_session_factory() as setup:
        job_id = _submit(setup, user_actor, fictional_incident.id, "job-fictional-lock")

    first = db_session_factory()
    second = db_session_factory()
    try:
        claimed = claim_job(first, job_id, now=FIXED_NOW)
        skipped = claim_job(second, job_id, now=FIXED_NOW)
        assert claimed is not None
        assert claimed.state == "running"
        assert claimed.stage == "classifying"
        assert skipped is None
        second.rollback()
        first.commit()
    finally:
        first.close()
        second.close()


def test_duplicate_redelivery_applies_one_terminal_result_and_one_audit(
    db_session, db_session_factory, user_actor, fictional_incident, fictional_report,
):
    db_session.commit()
    with db_session_factory() as setup:
        job_id = _submit(setup, user_actor, fictional_incident.id, "job-fictional-redelivery")

    with db_session_factory.begin() as worker:
        assert claim_job(worker, job_id, now=FIXED_NOW) is not None
        apply_job_result(worker, job_id, expected_incident_revision=1, now=FIXED_NOW)

    with db_session_factory.begin() as redelivery:
        assert claim_job(redelivery, job_id, now=FIXED_NOW) is None
        apply_job_result(redelivery, job_id, expected_incident_revision=1, now=FIXED_NOW)

    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert job.state == "succeeded"
        assert job.stage == "completed"
        assert job.attempts == 1
        assert verification.scalar(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.action == "ai.job_succeeded",
            AuditEvent.target_id == job_id,
        )) == 1


def test_stale_incident_revision_becomes_terminal_conflict_without_overwrite(
    db_session, db_session_factory, user_actor, fictional_incident, fictional_report,
):
    original_classification = dict(fictional_incident.classification)
    db_session.commit()
    with db_session_factory() as setup:
        job_id = _submit(setup, user_actor, fictional_incident.id, "job-fictional-stale-result")

    with db_session_factory.begin() as advance:
        incident = advance.get(type(fictional_incident), fictional_incident.id)
        incident.current_revision_number = 2
        incident.classification = {"category": "newer_fictional_value"}

    with db_session_factory.begin() as worker:
        assert claim_job(worker, job_id, now=FIXED_NOW) is not None
        apply_job_result(worker, job_id, expected_incident_revision=1, now=FIXED_NOW)

    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        incident = verification.get(type(fictional_incident), fictional_incident.id)
        assert job.state == "failed"
        assert job.stage == "failed"
        assert job.error_code == "job_result_conflict"
        assert incident.current_revision_number == 2
        assert incident.classification == {"category": "newer_fictional_value"}
        assert incident.classification != original_classification
        audit = verification.scalar(select(AuditEvent).where(
            AuditEvent.action == "ai.job_failed", AuditEvent.target_id == job_id,
        ))
        assert audit.details == {
            "job_id": str(job_id),
            "job_type": "classify",
            "result_code": "job_result_conflict",
        }
