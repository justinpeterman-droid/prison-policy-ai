"""Row-locked job claiming and stale-result protection (RP-06 service layer).

`claim_job()`/`apply_job_result()` are consumed by RP-07's dispatcher/worker,
which does not exist yet, so they are exercised directly here rather than
through HTTP.
"""
from datetime import timedelta

import pytest
from sqlalchemy import select

from backend.jobs.service import (
    JobResultConflict,
    SubmitJobCommand,
    apply_job_result,
    claim_job,
    submit_job,
)
from backend.persistence.models.jobs import AiJob, TaskOutbox
from backend.reports.persistence import save_incident_record
from backend.webapp.api_v1.schemas.reporting import SaveIncidentRequest


def _submit(session, actor, incident, *, key, now, job_type="classify", base=1):
    job = submit_job(
        session, actor, SubmitJobCommand(incident_id=incident.id, job_type=job_type),
        key, base, now=now, request_id=f"request_{key}", client_version="1.0.0",
    )
    session.commit()
    return job.id


def test_claim_job_uses_skip_locked_so_a_concurrent_claimer_never_double_processes(
    db_session, db_session_factory, fictional_incident, fictional_report,
    user_actor, identity_fixed_now,
):
    job_id = _submit(
        db_session, user_actor, fictional_incident,
        key="job-redelivery-claim-0001", now=identity_fixed_now,
    )

    holder = db_session_factory()
    contender = db_session_factory()
    try:
        held = claim_job(holder, job_id)
        assert held is not None
        assert held.state == "running"
        assert held.stage == "classifying"
        assert held.attempt_count == 1

        skipped = claim_job(contender, job_id)
        assert skipped is None

        holder.commit()
    finally:
        holder.close()
        contender.rollback()
        contender.close()

    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert job.state == "running"
        assert job.attempt_count == 1
        outbox = verification.scalar(
            select(TaskOutbox).where(TaskOutbox.ai_job_id == job_id))
        assert outbox.state == "dispatched"
        assert outbox.attempts == 1


def test_claim_job_returns_none_for_an_unknown_job(db_session_factory):
    from uuid import uuid4

    with db_session_factory() as session:
        assert claim_job(session, uuid4()) is None


def test_apply_job_result_succeeds_once_and_redelivery_is_a_safe_noop(
    db_session, db_session_factory, fictional_incident, fictional_report,
    user_actor, identity_fixed_now,
):
    job_id = _submit(
        db_session, user_actor, fictional_incident,
        key="job-redelivery-apply-0001", now=identity_fixed_now,
    )
    with db_session_factory() as claiming:
        assert claim_job(claiming, job_id) is not None
        claiming.commit()

    with db_session_factory() as applying:
        apply_job_result(applying, job_id, 1)
        applying.commit()

    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert job.state == "succeeded"
        assert job.stage == "completed"
        assert job.completed_at is not None
        first_completed_at = job.completed_at
        outbox = verification.scalar(
            select(TaskOutbox).where(TaskOutbox.ai_job_id == job_id))
        assert outbox.state == "completed"

    # A redelivered/duplicate Cloud Tasks delivery of an already-applied
    # result must be a safe no-op, not a second application.
    with db_session_factory() as reapplying:
        apply_job_result(reapplying, job_id, 1)
        reapplying.commit()

    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert job.state == "succeeded"
        assert job.completed_at == first_completed_at


def test_apply_job_result_rejects_a_stale_incident_revision(
    db_session, db_session_factory, fictional_incident, fictional_report,
    user_actor, identity_fixed_now,
):
    job_id = _submit(
        db_session, user_actor, fictional_incident,
        key="job-redelivery-stale-0001", now=identity_fixed_now,
    )
    with db_session_factory() as claiming:
        assert claim_job(claiming, job_id) is not None
        claiming.commit()

    # The incident moves after the job was queued.
    with db_session_factory() as saving:
        model = SaveIncidentRequest.model_validate({
            "field_notes": "Fictional updated field notes after the job was queued.",
            "base_revision_number": 1,
        })
        save_incident_record(
            saving, user_actor, fictional_incident.id, model,
            "job-redelivery-stale-save-0001",
            now=identity_fixed_now + timedelta(minutes=1),
            request_id="request_job_redelivery_stale_save", client_version="1.0.0",
        )
        saving.commit()

    with db_session_factory() as applying:
        with pytest.raises(JobResultConflict):
            apply_job_result(applying, job_id, 1)
        applying.commit()

    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert job.state == "failed"
        assert job.stage == "failed"
        assert job.error_code == "job_result_conflict"
        outbox = verification.scalar(
            select(TaskOutbox).where(TaskOutbox.ai_job_id == job_id))
        assert outbox.state == "failed"
        assert outbox.last_error_code == "job_result_conflict"

    # A stale-result failure is also terminal: redelivery is a safe no-op.
    with db_session_factory() as reapplying:
        apply_job_result(reapplying, job_id, 1)
        reapplying.commit()

    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert job.state == "failed"


def test_apply_job_result_on_an_unknown_job_raises_job_not_found(db_session_factory):
    from uuid import uuid4

    from backend.jobs.service import JobNotFound

    with db_session_factory() as session:
        with pytest.raises(JobNotFound):
            apply_job_result(session, uuid4(), 1)
