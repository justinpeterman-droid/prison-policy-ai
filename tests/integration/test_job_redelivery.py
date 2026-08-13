"""PostgreSQL locking and at-most-once durable AI-job result contracts."""

from datetime import UTC, datetime, timedelta
import json
from uuid import UUID

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from backend.persistence.models import AuditEvent
from backend.persistence.models.jobs import AiJob
from backend.jobs.service import (
    SubmitJobCommand,
    apply_job_result,
    claim_job,
    submit_job,
)


FIXED_NOW = datetime(2026, 8, 12, 15, 15, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _fictional_job_api_clock(monkeypatch, identity_fixed_now):
    import backend.webapp.api_v1.middleware as middleware

    fixed = identity_fixed_now + timedelta(minutes=1)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed if tz is not None else fixed.replace(tzinfo=None)

    monkeypatch.setattr(middleware, "datetime", _FixedDateTime)


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
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
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
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    with db_session_factory() as setup:
        job_id = _submit(setup, user_actor, fictional_incident.id, "job-fictional-redelivery")

    with db_session_factory.begin() as worker:
        claimed = claim_job(worker, job_id, now=FIXED_NOW)
        assert claimed is not None
        apply_job_result(
            worker,
            job_id,
            expected_incident_revision=1,
            claim_token=claimed.claim_token,
            now=FIXED_NOW,
        )

    with db_session_factory.begin() as redelivery:
        assert claim_job(redelivery, job_id, now=FIXED_NOW) is None
        apply_job_result(
            redelivery,
            job_id,
            expected_incident_revision=1,
            claim_token=UUID("00000000-0000-4000-8000-000000000699"),
            now=FIXED_NOW,
        )

    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert job.state == "succeeded"
        assert job.stage == "completed"
        assert job.attempts == 1
        assert (
            verification.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.action == "ai.job_succeeded",
                    AuditEvent.target_id == job_id,
                )
            )
            == 1
        )


def test_stale_incident_revision_becomes_terminal_conflict_without_overwrite(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
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
        claimed = claim_job(worker, job_id, now=FIXED_NOW)
        assert claimed is not None
        apply_job_result(
            worker,
            job_id,
            expected_incident_revision=1,
            claim_token=claimed.claim_token,
            now=FIXED_NOW,
        )

    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        incident = verification.get(type(fictional_incident), fictional_incident.id)
        assert job.state == "failed"
        assert job.stage == "failed"
        assert job.error_code == "job_result_conflict"
        assert incident.current_revision_number == 2
        assert incident.classification == {"category": "newer_fictional_value"}
        assert incident.classification != original_classification
        audit = verification.scalar(
            select(AuditEvent).where(
                AuditEvent.action == "ai.job_failed",
                AuditEvent.target_id == job_id,
            )
        )
        assert audit.details == {
            "job_id": str(job_id),
            "job_type": "classify",
            "result_code": "job_result_conflict",
        }


def test_expired_running_job_is_reclaimed_with_a_fenced_twenty_minute_lease(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    with db_session_factory() as setup:
        job_id = _submit(setup, user_actor, fictional_incident.id, "job-fictional-reclaim")

    with db_session_factory.begin() as first_delivery:
        first = claim_job(first_delivery, job_id, now=FIXED_NOW)
        assert first is not None
        first_token = first.claim_token
        assert first.lease_expires_at == FIXED_NOW + timedelta(minutes=20)

    with db_session_factory.begin() as early_redelivery:
        assert (
            claim_job(
                early_redelivery,
                job_id,
                now=FIXED_NOW + timedelta(minutes=19),
            )
            is None
        )

    reclaim_now = FIXED_NOW + timedelta(minutes=20, seconds=1)
    with db_session_factory.begin() as recovery_delivery:
        recovered = claim_job(recovery_delivery, job_id, now=reclaim_now)
        assert recovered is not None
        recovered_token = recovered.claim_token
        assert recovered_token != first_token
        assert recovered.attempts == 2
        assert recovered.lease_expires_at == reclaim_now + timedelta(minutes=20)

    with db_session_factory.begin() as stale_worker:
        with pytest.raises(ValueError, match="claim"):
            apply_job_result(
                stale_worker,
                job_id,
                expected_incident_revision=1,
                claim_token=first_token,
                result_reference={"incident_revision_number": 1},
                now=reclaim_now,
            )

    with db_session_factory.begin() as recovered_worker:
        apply_job_result(
            recovered_worker,
            job_id,
            expected_incident_revision=1,
            claim_token=recovered_token,
            result_reference={"incident_revision_number": 1},
            now=reclaim_now,
        )

    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert job.state == "succeeded"
        assert job.attempts == 2
        assert job.claim_token is None
        assert job.lease_expires_at is None
        assert job.result_reference == {"incident_revision_number": 1}
        assert (
            verification.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.action == "ai.job_succeeded",
                    AuditEvent.target_id == job_id,
                )
            )
            == 1
        )


@pytest.mark.parametrize(
    "unsafe_reference",
    [
        {"report_text": "Fictional sensitive report content."},
        {"provider": {"prompt": "Fictional prompt.", "response": "Fictional output."}},
        {"raw": {"field_notes": "Fictional sensitive field notes."}},
        {
            "reports": [
                {
                    "report_id": "00000000-0000-4000-8000-000000000613",
                    "revision_number": 1,
                    "narrative": "Fictional sensitive narrative.",
                }
            ],
        },
    ],
)
def test_worker_result_rejects_content_provider_unknown_and_nested_fields_atomically(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
    unsafe_reference,
):
    db_session.commit()
    with db_session_factory() as setup:
        job_id = _submit(
            setup,
            user_actor,
            fictional_incident.id,
            f"job-fictional-unsafe-{len(str(unsafe_reference))}",
        )

    with db_session_factory.begin() as worker:
        claimed = claim_job(worker, job_id, now=FIXED_NOW)
        assert claimed is not None
        claim_token = claimed.claim_token

    with db_session_factory.begin() as apply_session:
        with pytest.raises(ValueError, match="result reference"):
            apply_job_result(
                apply_session,
                job_id,
                expected_incident_revision=1,
                claim_token=claim_token,
                result_reference=unsafe_reference,
                now=FIXED_NOW,
            )

    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert job.state == "running"
        assert job.stage == "classifying"
        assert job.result_reference == {}
        assert job.completed_at is None
        assert (
            verification.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.target_id == job_id,
                    AuditEvent.action.in_(("ai.job_succeeded", "ai.job_failed")),
                )
            )
            == 0
        )


def test_worker_result_rejects_safe_shaped_references_that_are_not_durable_targets(
    db_session,
    db_session_factory,
    user_actor,
    fictional_incident,
    fictional_report,
):
    db_session.commit()
    with db_session_factory() as setup:
        job_id = _submit(
            setup,
            user_actor,
            fictional_incident.id,
            "job-fictional-missing-result-target",
        )

    with db_session_factory.begin() as worker:
        claimed = claim_job(worker, job_id, now=FIXED_NOW)
        assert claimed is not None
        claim_token = claimed.claim_token

    with db_session_factory.begin() as apply_session:
        with pytest.raises(ValueError, match="result reference"):
            apply_job_result(
                apply_session,
                job_id,
                expected_incident_revision=1,
                claim_token=claim_token,
                result_reference={
                    "incident_revision_number": 999,
                    "reports": [
                        {
                            "report_id": "00000000-0000-4000-8000-000000000699",
                            "revision_number": 1,
                        }
                    ],
                },
                now=FIXED_NOW,
            )

    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert job.state == "running"
        assert job.result_reference == {}
        assert job.completed_at is None


def test_safe_result_reference_is_canonical_and_status_get_returns_only_safe_ids(
    db_session,
    db_session_factory,
    api_client,
    owner_bearer_headers,
    user_actor,
    fictional_incident,
    fictional_report,
):
    incident_id = fictional_incident.id
    report_id = fictional_report.id
    db_session.commit()
    submitted = api_client.post(
        f"/api/v1/incidents/{incident_id}/jobs/generate",
        headers=owner_bearer_headers
        | {
            "Idempotency-Key": "job-fictional-safe-result",
            "X-Request-ID": "request_job_fictional_safe_result",
        },
        json={"base_revision_number": 1},
    )
    assert submitted.status_code == 202
    job_id = UUID(submitted.json["data"]["id"])

    with db_session_factory.begin() as worker:
        claimed = claim_job(worker, job_id, now=FIXED_NOW)
        assert claimed is not None
        apply_job_result(
            worker,
            job_id,
            expected_incident_revision=1,
            claim_token=claimed.claim_token,
            result_reference={
                "reports": [{"revision_number": 1, "report_id": str(report_id)}],
                "incident_revision_number": 1,
            },
            now=FIXED_NOW,
        )

    response = api_client.get(
        f"/api/v1/jobs/{job_id}",
        headers=owner_bearer_headers
        | {
            "X-Request-ID": "request_job_fictional_safe_status",
        },
    )
    assert response.status_code == 200
    assert response.json["data"]["result_reference"] == {
        "incident_revision_number": 1,
        "reports": [{"report_id": str(report_id), "revision_number": 1}],
    }


def test_status_get_never_reflects_a_malformed_durable_result_reference(
    db_session,
    db_session_factory,
    api_client,
    owner_bearer_headers,
    fictional_incident,
    fictional_report,
):
    incident_id = fictional_incident.id
    db_session.commit()
    submitted = api_client.post(
        f"/api/v1/incidents/{incident_id}/jobs/classify",
        headers=owner_bearer_headers
        | {
            "Idempotency-Key": "job-fictional-corrupt-result",
            "X-Request-ID": "request_job_fictional_corrupt_result",
        },
        json={"base_revision_number": 1},
    )
    assert submitted.status_code == 202
    job_id = UUID(submitted.json["data"]["id"])
    marker = "FICTIONAL_PRIVATE_PROVIDER_OUTPUT_MUST_NOT_ESCAPE"

    with pytest.raises(IntegrityError):
        with db_session_factory.begin() as corrupt:
            corrupt.execute(
                text("UPDATE ai_jobs SET result_reference=CAST(:reference AS jsonb) WHERE id=:job_id"),
                {
                    "job_id": job_id,
                    "reference": json.dumps(
                        {
                            "reports": [
                                {
                                    "report_id": "00000000-0000-4000-8000-000000000613",
                                    "revision_number": 1,
                                    "provider_output": marker,
                                }
                            ],
                        }
                    ),
                },
            )

    response = api_client.get(
        f"/api/v1/jobs/{job_id}",
        headers=owner_bearer_headers
        | {
            "X-Request-ID": "request_job_fictional_corrupt_status",
        },
    )
    assert response.status_code == 200
    assert response.json["data"]["result_reference"] == {}
    assert marker not in response.get_data(as_text=True)
