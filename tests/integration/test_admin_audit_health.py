"""RP-10 elevated operational endpoints use only bounded, safe values."""
from datetime import UTC, datetime

import pytest

from tests.integration.identity_fixtures import bearer_headers


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


def test_elevated_overview_health_and_audit_list_are_safe(api_client, admin_bearer_headers, db_session, monkeypatch):
    import backend.webapp.api_v1.admin_health as health_api
    db_session.commit()
    signals = []
    monkeypatch.setattr(health_api, "_emit", lambda signal, result, **_fields: signals.append((signal, result)))
    _elevate(api_client, admin_bearer_headers)
    overview = api_client.get("/api/v1/admin/overview", headers=_headers(admin_bearer_headers, "overview"))
    assert overview.status_code == 200
    assert set(overview.get_json()["data"]) == {"reports", "queued_jobs", "pending_outbox", "recent_audit_events", "build"}
    health = api_client.get("/api/v1/admin/health", headers=_headers(admin_bearer_headers, "health"))
    assert health.status_code == 200, health.get_json()
    payload = health.get_json()["data"]
    assert payload["status"] in {"Operational", "Degraded", "Unavailable"}
    assert {item["component"] for item in payload["components"]} == {
        "database", "policy_search", "queue", "backup_restore",
    }
    assert next(
        item["status"] for item in payload["components"]
        if item["component"] == "policy_search"
    ) in {"Operational", "Degraded", "Unavailable"}
    for signal in ("dependency_health", "queue_health", "backup_restore_health"):
        assert signal in {name for name, _result in signals}


def test_health_emits_bounded_policy_search_and_failed_job_signals(
    api_client, admin_bearer_headers, db_session, monkeypatch,
):
    import backend.webapp.api_v1.admin_health as health_api

    signals = []
    monkeypatch.setattr(
        health_api, "_emit",
        lambda signal, result, **fields: signals.append((signal, result, fields)),
    )
    monkeypatch.setattr(
        health_api, "_failed_job_types",
        lambda _session: ("generate",),
    )
    db_session.commit()
    _elevate(api_client, admin_bearer_headers)

    response = api_client.get(
        "/api/v1/admin/health", headers=_headers(admin_bearer_headers, "bounded-signals"),
    )

    assert response.status_code == 200, response.get_json()
    assert ("dependency_health", "operational", {
        "dependency": "policy_search", "latency_bucket": "unknown",
    }) in signals
    assert ("queue_health", "failed", {
        "depth_bucket": "unknown", "oldest_age_bucket": "unknown",
        "job_type": "generate", "stage": "failed", "latency_bucket": "unknown",
    }) in signals
    page = api_client.get("/api/v1/admin/audit-events?limit=50", headers=_headers(admin_bearer_headers, "audit"))
    assert page.status_code == 200, page.get_json()
    for event in page.get_json()["data"]["items"]:
        assert set(event) == {"event_id", "occurred_at", "actor_account_id", "actor_staff_member_id", "action", "target_type", "target_id", "result", "details"}
        assert "device_id_hash" not in event and "network_hash" not in event


def test_audit_export_requires_step_up_and_has_fixed_safe_columns(api_client, admin_bearer_headers, db_session):
    db_session.commit()
    _elevate(api_client, admin_bearer_headers)
    headers = _headers(admin_bearer_headers, "audit-export") | {"Idempotency-Key": "rp10-audit-export-0001"}
    body = {"filters": {"action_family": "admin"}, "format": "csv", "reason": "Fictional records fixture."}
    denied = api_client.post("/api/v1/admin/audit-events/export", headers=headers, json=body)
    assert denied.status_code == 403
    step = api_client.post(
        "/api/v1/auth/admin-step-up",
        headers=_headers(admin_bearer_headers, "audit-step") | {"Idempotency-Key": "rp10-audit-step-0001"},
        json={"pin": ADMIN_PIN, "purpose": "audit_export"},
    )
    token = step.get_json()["data"]["step_up_token"]
    response = api_client.post(
        "/api/v1/admin/audit-events/export",
        headers=headers | {"X-Admin-Step-Up": token}, json=body,
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
        headers=_headers(admin_bearer_headers, "audit-step-replay") | {"Idempotency-Key": "rp10-audit-step-0002"},
        json={"pin": ADMIN_PIN, "purpose": "audit_export"},
    )
    replay = api_client.post(
        "/api/v1/admin/audit-events/export",
        headers=_headers(admin_bearer_headers, "audit-export-replay")
        | {"Idempotency-Key": "rp10-audit-export-0001", "X-Admin-Step-Up": replay_step.get_json()["data"]["step_up_token"]},
        json=body,
    )
    assert replay.status_code == 200, replay.get_json()
    assert replay.get_data() == response.get_data()
    assert "details" not in response.get_data(as_text=True).splitlines()[0]
