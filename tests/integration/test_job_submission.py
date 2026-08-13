"""One-transaction idempotent AI job submission and safe job status.

`submit_job()` is exercised only through the HTTP surface here; row-locked
claiming and stale-result guards are covered directly at the service layer
in `tests/integration/test_job_redelivery.py`.
"""
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from backend.persistence.models.jobs import AiJob, TaskOutbox
from backend.persistence.models.security import AuditEvent, IdempotencyRecord


@pytest.fixture(autouse=True)
def _fictional_access_api_environment(monkeypatch, identity_fixed_now):
    monkeypatch.setenv("ACCESS_API_ENABLED", "true")
    monkeypatch.setenv("IDENTITY_HASH_PEPPER", "p" * 32)
    monkeypatch.setenv("CURSOR_SIGNING_KEY", "c" * 32)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://api.example.gov")

    import backend.webapp.api_v1.middleware as middleware

    fixed = identity_fixed_now + timedelta(minutes=1)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed if tz is not None else fixed.replace(tzinfo=None)

    monkeypatch.setattr(middleware, "datetime", _FixedDateTime)


def _headers(base_headers, key):
    return base_headers | {"Idempotency-Key": key}


def test_same_idempotency_key_returns_same_job(
    api_client, db_session, owner_bearer_headers, incident_id, fictional_report,
):
    db_session.commit()
    headers = owner_bearer_headers | {"Idempotency-Key": "job-fictional-0001"}
    first = api_client.post(
        f"/api/v1/incidents/{incident_id}/jobs/classify",
        headers=headers, json={"base_revision_number": 1},
    )
    second = api_client.post(
        f"/api/v1/incidents/{incident_id}/jobs/classify",
        headers=headers, json={"base_revision_number": 1},
    )
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json["data"]["id"] == second.json["data"]["id"]


def test_changed_payload_with_same_key_conflicts(
    api_client, db_session, owner_bearer_headers, incident_id, fictional_report,
):
    db_session.commit()
    headers = owner_bearer_headers | {"Idempotency-Key": "job-fictional-0002"}
    api_client.post(
        f"/api/v1/incidents/{incident_id}/jobs/extract",
        headers=headers, json={"base_revision_number": 1},
    )
    response = api_client.post(
        f"/api/v1/incidents/{incident_id}/jobs/extract",
        headers=headers, json={"base_revision_number": 2},
    )
    assert response.status_code == 409
    assert response.json["error"]["code"] == "idempotency_conflict"


def test_submission_creates_queued_job_pending_outbox_and_audit_row(
    api_client, db_session, owner_bearer_headers, incident_id, fictional_report, db_session_factory,
):
    db_session.commit()
    headers = _headers(owner_bearer_headers, "job-fictional-0003")
    response = api_client.post(
        f"/api/v1/incidents/{incident_id}/jobs/disciplinary",
        headers=headers, json={"base_revision_number": 1},
    )
    assert response.status_code == 202
    body = response.json["data"]
    assert body["job_type"] == "disciplinary"
    assert body["state"] == "queued"
    assert body["stage"] == "queued"
    assert body["incident_id"] == str(incident_id)
    job_id = UUID(body["id"])

    with db_session_factory() as verification:
        job = verification.get(AiJob, job_id)
        assert job is not None
        assert job.state == "queued"
        assert job.stage == "queued"
        assert job.job_type == "disciplinary"
        assert job.incident_id == incident_id
        assert job.expected_incident_revision_number == 1

        outbox = verification.scalar(
            select(TaskOutbox).where(TaskOutbox.ai_job_id == job_id))
        assert outbox is not None
        assert outbox.state == "pending"
        assert outbox.attempts == 0

        audit_count = verification.scalar(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.action == "ai.job_submitted", AuditEvent.target_id == job_id,
        ))
        assert audit_count == 1


def test_rollback_on_unknown_incident_leaves_no_orphan_job_outbox_or_audit_row(
    api_client, db_session, owner_bearer_headers, db_session_factory,
):
    db_session.commit()
    unknown_incident_id = uuid4()
    headers = _headers(owner_bearer_headers, "job-fictional-0004")
    response = api_client.post(
        f"/api/v1/incidents/{unknown_incident_id}/jobs/classify",
        headers=headers, json={"base_revision_number": 1},
    )
    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"

    with db_session_factory() as verification:
        assert verification.scalar(select(func.count()).select_from(AiJob)) == 0
        assert verification.scalar(select(func.count()).select_from(TaskOutbox)) == 0
        assert verification.scalar(select(func.count()).select_from(IdempotencyRecord)) == 0
        assert verification.scalar(select(func.count()).select_from(AuditEvent)) == 0


def test_unrelated_actor_is_concealed_and_leaves_no_orphan_rows(
    api_client, db_session, unrelated_bearer_headers, incident_id, db_session_factory,
):
    db_session.commit()
    headers = _headers(unrelated_bearer_headers, "job-fictional-0005")
    response = api_client.post(
        f"/api/v1/incidents/{incident_id}/jobs/classify",
        headers=headers, json={"base_revision_number": 1},
    )
    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"

    with db_session_factory() as verification:
        assert verification.scalar(select(func.count()).select_from(AiJob)) == 0
        assert verification.scalar(select(func.count()).select_from(TaskOutbox)) == 0


def test_stale_base_revision_is_rejected_with_revision_conflict(
    api_client, db_session, owner_bearer_headers, incident_id, fictional_report, db_session_factory,
):
    db_session.commit()
    headers = _headers(owner_bearer_headers, "job-fictional-0006")
    response = api_client.post(
        f"/api/v1/incidents/{incident_id}/jobs/generate",
        headers=headers, json={"base_revision_number": 99},
    )
    assert response.status_code == 409
    assert response.json["error"]["code"] == "revision_conflict"
    assert response.json["error"]["details"]["current_revision_number"] == 1

    with db_session_factory() as verification:
        assert verification.scalar(select(func.count()).select_from(AiJob)) == 0
        assert verification.scalar(select(func.count()).select_from(TaskOutbox)) == 0
        assert verification.scalar(select(func.count()).select_from(IdempotencyRecord)) == 0


def test_missing_idempotency_key_is_rejected(
    api_client, db_session, owner_bearer_headers, incident_id, fictional_report,
):
    db_session.commit()
    response = api_client.post(
        f"/api/v1/incidents/{incident_id}/jobs/classify",
        headers=owner_bearer_headers, json={"base_revision_number": 1},
    )
    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"


def test_closed_request_schema_rejects_unknown_fields(
    api_client, db_session, owner_bearer_headers, incident_id, fictional_report,
):
    db_session.commit()
    headers = _headers(owner_bearer_headers, "job-fictional-0007")
    response = api_client.post(
        f"/api/v1/incidents/{incident_id}/jobs/classify",
        headers=headers,
        json={"base_revision_number": 1, "requested_by_account_id": str(uuid4())},
    )
    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_failed"


def test_get_job_status_is_readable_by_owner_and_admin_but_concealed_from_unrelated(
    api_client, db_session, owner_bearer_headers, admin_bearer_headers,
    unrelated_bearer_headers, incident_id, fictional_report,
):
    db_session.commit()
    headers = _headers(owner_bearer_headers, "job-fictional-0008")
    submitted = api_client.post(
        f"/api/v1/incidents/{incident_id}/jobs/generate",
        headers=headers, json={"base_revision_number": 1},
    )
    assert submitted.status_code == 202
    job_id = submitted.json["data"]["id"]

    owner_read = api_client.get(f"/api/v1/jobs/{job_id}", headers=owner_bearer_headers)
    assert owner_read.status_code == 200
    assert owner_read.json["data"]["state"] == "queued"
    assert owner_read.json["data"]["stage"] == "queued"
    assert owner_read.json["data"]["job_type"] == "generate"

    admin_read = api_client.get(f"/api/v1/jobs/{job_id}", headers=admin_bearer_headers)
    assert admin_read.status_code == 200
    assert admin_read.json["data"]["id"] == job_id

    unrelated_read = api_client.get(f"/api/v1/jobs/{job_id}", headers=unrelated_bearer_headers)
    assert unrelated_read.status_code == 404
    assert unrelated_read.json["error"]["code"] == "not_found"


def test_unknown_job_id_is_not_found(api_client, db_session, owner_bearer_headers):
    db_session.commit()
    response = api_client.get(f"/api/v1/jobs/{uuid4()}", headers=owner_bearer_headers)
    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"


def test_every_job_type_submission_path_is_wired(
    api_client, db_session, owner_bearer_headers, incident_id, fictional_report,
):
    db_session.commit()
    for index, job_type in enumerate(("classify", "extract", "generate", "disciplinary")):
        headers = _headers(owner_bearer_headers, f"job-fictional-path-{index:04d}")
        response = api_client.post(
            f"/api/v1/incidents/{incident_id}/jobs/{job_type}",
            headers=headers, json={"base_revision_number": 1},
        )
        assert response.status_code == 202, job_type
        assert response.json["data"]["job_type"] == job_type
