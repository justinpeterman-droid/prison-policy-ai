"""RP-10 elevated operational endpoints use only bounded, safe values."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from backend.persistence.models import AiJob, TaskOutbox

import pytest


ADMIN_PIN = "Q7W9E2"


@pytest.fixture
def identity_fixed_now():
    """Keep access credentials valid for this live endpoint integration test."""
    return datetime.now(UTC)


def _headers(headers, suffix):
    return headers | {"X-Request-ID": f"request-rp10-{suffix}"}


def _elevate(client, headers):
    response = client.post(
        "/api/v1/auth/admin-step-up",
        headers=_headers(headers, "elevate") | {"Idempotency-Key": "rp10-elevate-0001"},
        json={"pin": ADMIN_PIN, "purpose": "admin_center"},
    )
    assert response.status_code == 200, response.get_json()


def test_elevated_overview_health_and_audit_list_are_safe(
    api_client, admin_bearer_headers, db_session, monkeypatch
):
    import backend.webapp.api_v1.admin_health as health_api

    db_session.commit()
    signals = []
    monkeypatch.setattr(
        health_api,
        "_emit",
        lambda signal, result, **_fields: signals.append((signal, result)),
    )
    _elevate(api_client, admin_bearer_headers)
    overview = api_client.get(
        "/api/v1/admin/overview", headers=_headers(admin_bearer_headers, "overview")
    )
    assert overview.status_code == 200
    assert set(overview.get_json()["data"]) == {
        "reports",
        "queued_jobs",
        "pending_outbox",
        "recent_audit_events",
        "build",
    }
    health = api_client.get(
        "/api/v1/admin/health", headers=_headers(admin_bearer_headers, "health")
    )
    assert health.status_code == 200, health.get_json()
    payload = health.get_json()["data"]
    assert payload["status"] in {"Operational", "Degraded", "Unavailable"}
    assert {item["component"] for item in payload["components"]} == {
        "database",
        "policy_search",
        "queue",
        "backup_restore",
    }
    assert next(
        item["status"]
        for item in payload["components"]
        if item["component"] == "policy_search"
    ) in {"Operational", "Degraded", "Unavailable"}
    for signal in ("dependency_health", "queue_health", "backup_restore_health"):
        assert signal in {name for name, _result in signals}


def test_health_emits_bounded_policy_search_and_failed_job_signals(
    api_client,
    admin_bearer_headers,
    db_session,
    monkeypatch,
):
    import backend.webapp.api_v1.admin_health as health_api

    signals = []
    monkeypatch.setattr(
        health_api,
        "_emit",
        lambda signal, result, **fields: signals.append((signal, result, fields)),
    )
    monkeypatch.setattr(
        health_api,
        "_failed_job_health",
        lambda _session: (("generate", "unknown"),),
    )
    db_session.commit()
    _elevate(api_client, admin_bearer_headers)

    response = api_client.get(
        "/api/v1/admin/health",
        headers=_headers(admin_bearer_headers, "bounded-signals"),
    )

    assert response.status_code == 200, response.get_json()
    assert (
        "dependency_health",
        "unavailable",
        {
            "dependency": "policy_search",
            "latency_bucket": "unknown",
        },
    ) in signals
    assert (
        "queue_health",
        "failed",
        {
            "depth_bucket": "unknown",
            "oldest_age_bucket": "unknown",
            "job_type": "generate",
            "stage": "failed",
            "latency_bucket": "unknown",
        },
    ) in signals
    page = api_client.get(
        "/api/v1/admin/audit-events?limit=50",
        headers=_headers(admin_bearer_headers, "audit"),
    )
    assert page.status_code == 200, page.get_json()
    for event in page.get_json()["data"]["items"]:
        assert set(event) == {
            "event_id",
            "occurred_at",
            "actor_account_id",
            "actor_staff_member_id",
            "action",
            "target_type",
            "target_id",
            "result",
            "details",
        }
        assert "device_id_hash" not in event and "network_hash" not in event


def test_health_age_bucket_contract_is_explicit_and_non_identifying():
    """The producer has a closed bucket contract before any durable query uses it."""
    import backend.webapp.api_v1.admin_health as health_api

    assert callable(getattr(health_api, "_age_bucket", None))
    assert health_api._age_bucket(timedelta(seconds=0)) == "less_than_1m"
    assert health_api._age_bucket(timedelta(minutes=1)) == "1m_to_5m"
    assert health_api._age_bucket(timedelta(minutes=5)) == "5m_to_30m"
    assert health_api._age_bucket(timedelta(minutes=30)) == "30m_to_2h"
    assert health_api._age_bucket(timedelta(hours=2)) == "2h_or_more"
    assert health_api._QUEUE_AGE_BUCKETS == (
        "zero",
        "less_than_1m",
        "1m_to_5m",
        "5m_to_30m",
        "30m_to_2h",
        "2h_or_more",
    )


def test_health_stage_latency_bucket_contract_has_distinct_second_boundaries():
    """Failed-job stage latency uses its own closed, second-scale enum."""
    import backend.webapp.api_v1.admin_health as health_api

    assert callable(getattr(health_api, "_latency_bucket", None))
    assert health_api._STAGE_LATENCY_BUCKETS == (
        "less_than_1s",
        "1s_to_10s",
        "10s_to_60s",
        "1m_to_5m",
        "5m_or_more",
    )
    assert health_api._latency_bucket(timedelta(seconds=0)) == "less_than_1s"
    assert health_api._latency_bucket(timedelta(seconds=1)) == "1s_to_10s"
    assert health_api._latency_bucket(timedelta(seconds=10)) == "10s_to_60s"
    assert health_api._latency_bucket(timedelta(seconds=45)) == "10s_to_60s"
    assert health_api._latency_bucket(timedelta(seconds=60)) == "1m_to_5m"
    assert health_api._latency_bucket(timedelta(minutes=5)) == "5m_or_more"


def test_health_emits_bucketed_queue_age_and_failed_stage_latency(
    api_client,
    admin_bearer_headers,
    owner_bearer_headers,
    db_session,
    fictional_incident,
    monkeypatch,
):
    """Health telemetry projects durable lifecycle timestamps into safe buckets."""
    import backend.webapp.api_v1.admin_health as health_api

    now = datetime.now(UTC)
    queued = api_client.post(
        f"/api/v1/incidents/{fictional_incident.id}/jobs/classify",
        headers=owner_bearer_headers
        | {
            "Idempotency-Key": "rp10-health-queued-0001",
            "X-Request-ID": "request-rp10-health-queued",
        },
        json={"base_revision_number": 1},
    )
    assert queued.status_code == 202, queued.get_json()
    job = db_session.get(AiJob, queued.get_json()["data"]["id"])
    assert job is not None
    pending_outbox = db_session.scalar(
        select(TaskOutbox).where(TaskOutbox.ai_job_id == job.id)
    )
    assert pending_outbox is not None
    pending_outbox.created_at = now - timedelta(minutes=45)

    failed = api_client.post(
        f"/api/v1/incidents/{fictional_incident.id}/jobs/generate",
        headers=owner_bearer_headers
        | {
            "Idempotency-Key": "rp10-health-failed-0001",
            "X-Request-ID": "request-rp10-health-failed",
        },
        json={"base_revision_number": 1},
    )
    assert failed.status_code == 202, failed.get_json()
    failed_job = db_session.get(AiJob, failed.get_json()["data"]["id"])
    assert failed_job is not None
    failed_job.state = "failed"
    failed_job.stage = "failed"
    failed_job.started_at = now - timedelta(seconds=75)
    failed_job.completed_at = now - timedelta(seconds=30)
    db_session.commit()

    signals = []
    monkeypatch.setattr(
        health_api,
        "_emit",
        lambda signal, result, **fields: signals.append((signal, result, fields)),
    )
    _elevate(api_client, admin_bearer_headers)
    response = api_client.get(
        "/api/v1/admin/health",
        headers=_headers(admin_bearer_headers, "lifecycle-buckets"),
    )

    assert response.status_code == 200, response.get_json()
    assert (
        "queue_health",
        "operational",
        {
            "depth_bucket": "one_to_999",
            "oldest_age_bucket": "30m_to_2h",
        },
    ) in signals
    assert (
        "queue_health",
        "failed",
        {
            "depth_bucket": "unknown",
            "oldest_age_bucket": "unknown",
            "job_type": "generate",
            "stage": "failed",
            "latency_bucket": "10s_to_60s",
        },
    ) in signals


def test_audit_export_requires_step_up_and_has_fixed_safe_columns(
    api_client, admin_bearer_headers, db_session
):
    db_session.commit()
    _elevate(api_client, admin_bearer_headers)
    headers = _headers(admin_bearer_headers, "audit-export") | {
        "Idempotency-Key": "rp10-audit-export-0001"
    }
    body = {
        "filters": {"action_family": "admin"},
        "format": "csv",
        "reason": "Fictional records fixture.",
    }
    denied = api_client.post(
        "/api/v1/admin/audit-events/export", headers=headers, json=body
    )
    assert denied.status_code == 403
    step = api_client.post(
        "/api/v1/auth/admin-step-up",
        headers=_headers(admin_bearer_headers, "audit-step")
        | {"Idempotency-Key": "rp10-audit-step-0001"},
        json={"pin": ADMIN_PIN, "purpose": "audit_export"},
    )
    token = step.get_json()["data"]["step_up_token"]
    response = api_client.post(
        "/api/v1/admin/audit-events/export",
        headers=headers | {"X-Admin-Step-Up": token},
        json=body,
    )
    assert response.status_code == 200, response.get_json()
    assert response.mimetype == "text/csv"
    assert response.get_data(as_text=True).splitlines()[0] == (
        "event_id,occurred_at,actor_account_id,actor_staff_member_id,action,target_type,target_id,result"
    )
    assert response.headers["X-Audit-Row-Count"].isdigit()
    assert response.headers["Digest"].startswith("sha-256=")
    assert len(response.headers["Digest"].removeprefix("sha-256=")) == 44
    replay_step = api_client.post(
        "/api/v1/auth/admin-step-up",
        headers=_headers(admin_bearer_headers, "audit-step-replay")
        | {"Idempotency-Key": "rp10-audit-step-0002"},
        json={"pin": ADMIN_PIN, "purpose": "audit_export"},
    )
    replay = api_client.post(
        "/api/v1/admin/audit-events/export",
        headers=_headers(admin_bearer_headers, "audit-export-replay")
        | {
            "Idempotency-Key": "rp10-audit-export-0001",
            "X-Admin-Step-Up": replay_step.get_json()["data"]["step_up_token"],
        },
        json=body,
    )
    assert replay.status_code == 200, replay.get_json()
    assert replay.get_data() == response.get_data()
    assert "details" not in response.get_data(as_text=True).splitlines()[0]
