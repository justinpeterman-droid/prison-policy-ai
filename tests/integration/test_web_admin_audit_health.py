from datetime import UTC, datetime, timedelta

from backend.identity.audit import AuditEventInput, PostgresAuditWriter
from backend.persistence.models.security import AuditEvent
from tests.integration.identity_fixtures import issue_fictional_tokens
from tests.support.web_browser import authenticate_browser, browser_headers


def _authenticate_and_elevate(
    monkeypatch,
    api_client,
    db_session,
    db_session_factory,
    account,
):
    tokens = issue_fictional_tokens(
        db_session,
        account=account,
        device_id="device-fictional-admin-audit-health",
        now=datetime.now(UTC),
    )
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        account,
        session_id=tokens.session_id,
        device_id="device-fictional-admin-audit-health",
    )
    response = api_client.post(
        "/api/web/v1/admin/elevation",
        json={"pin": "Q7W9E2"},
        headers=browser_headers("request-admin-audit-health-elevation"),
    )
    assert response.status_code == 200, response.get_json()


def test_admin_audit_list_detail_filters_and_fail_closed_details(
    api_client,
    db_session,
    db_session_factory,
    fictional_staff_and_accounts,
    monkeypatch,
):
    accounts = fictional_staff_and_accounts
    writer = PostgresAuditWriter()
    valid_event_id = writer.append(db_session, AuditEventInput(
        actor_account_id=accounts.admin.id,
        actor_staff_member_id=accounts.admin.staff_member_id,
        action="admin.staff_updated",
        result="success",
        request_id="request-audit-safe-event",
        target_type="staff_member",
        target_id=accounts.user.staff_member_id,
        details={
            "target_staff_id": str(accounts.user.staff_member_id),
            "changed_fields": ["shift"],
        },
        client_version="1.0.0",
    ))
    unsafe = AuditEvent(
        actor_account_id=accounts.admin.id,
        actor_staff_member_id=accounts.admin.staff_member_id,
        action="admin.staff_updated",
        target_type="staff_member",
        target_id=accounts.preparer.staff_member_id,
        result="success",
        request_id="request-audit-unsafe-historical",
        client_version="1.0.0",
        details={
            "narrative": "this historical unsafe detail must never leave the API",
            "pin": "Q7W9E2",
            "token": "fictional-secret-token",
        },
        occurred_at=datetime.now(UTC) + timedelta(seconds=1),
    )
    db_session.add(unsafe)
    db_session.commit()

    _authenticate_and_elevate(
        monkeypatch, api_client, db_session, db_session_factory, accounts.admin,
    )

    response = api_client.get(
        "/api/web/v1/admin/audit?action_family=admin&result=success&limit=10",
        headers=browser_headers("request-admin-audit-list"),
    )
    assert response.status_code == 200, response.get_json()
    data = response.get_json()["data"]
    assert len(data["items"]) >= 2
    assert data["next_cursor"] is None
    by_id = {item["event_id"]: item for item in data["items"]}
    safe = by_id[str(valid_event_id)]
    assert safe["action"] == "admin.staff_updated"
    assert safe["details"]["changed_fields"] == ["shift"]
    unsafe_item = by_id[str(unsafe.id)]
    assert unsafe_item["details"] == {}
    serialized = repr(data).lower()
    for forbidden in (
        "historical unsafe detail",
        "q7w9e2",
        "fictional-secret-token",
        "pin_hash",
        "access_token",
        "renewal_token",
        "narrative",
    ):
        assert forbidden not in serialized

    detail = api_client.get(
        f"/api/web/v1/admin/audit/{valid_event_id}",
        headers=browser_headers("request-admin-audit-detail"),
    )
    assert detail.status_code == 200, detail.get_json()
    assert detail.get_json()["data"]["event_id"] == str(valid_event_id)
    assert detail.get_json()["data"]["request_id"] == "request-audit-safe-event"

    immutable = api_client.post(
        "/api/web/v1/admin/audit",
        json={},
        headers=browser_headers("request-admin-audit-no-mutation"),
    )
    assert immutable.status_code == 405


def test_admin_health_returns_only_safe_operational_statuses(
    api_client,
    db_session,
    db_session_factory,
    fictional_staff_and_accounts,
    monkeypatch,
):
    accounts = fictional_staff_and_accounts
    _authenticate_and_elevate(
        monkeypatch, api_client, db_session, db_session_factory, accounts.admin,
    )

    response = api_client.get(
        "/api/web/v1/admin/health",
        headers=browser_headers("request-admin-health"),
    )
    assert response.status_code == 200, response.get_json()
    data = response.get_json()["data"]
    assert set(data) == {"checked_at", "components", "build", "notices"}
    assert set(data["components"]) == {
        "api",
        "database",
        "ai",
        "policy_expert",
        "queue",
        "backups",
    }
    allowed = {"Operational", "Degraded", "Unavailable"}
    assert set(data["components"].values()) <= allowed
    assert isinstance(data["checked_at"], str)
    assert set(data["build"]) == {
        "source_commit", "cloud_run_revision", "alembic_revision",
    }
    assert isinstance(data["notices"], list)
    assert len(data["notices"]) <= 10
    serialized = repr(data).lower()
    for forbidden in (
        "database_url",
        "password",
        "secret",
        "token",
        "traceback",
        "exception",
        "sqlstate",
        "connection string",
    ):
        assert forbidden not in serialized


def test_regular_user_cannot_read_admin_audit_or_health(
    api_client,
    db_session,
    db_session_factory,
    fictional_user_account,
    monkeypatch,
):
    tokens = issue_fictional_tokens(
        db_session,
        account=fictional_user_account,
        device_id="device-fictional-user-admin-audit-health",
        now=datetime.now(UTC),
    )
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        fictional_user_account,
        session_id=tokens.session_id,
        device_id="device-fictional-user-admin-audit-health",
    )

    for path in ("/api/web/v1/admin/audit", "/api/web/v1/admin/health"):
        response = api_client.get(
            path,
            headers=browser_headers("request-user-admin-audit-health-denied"),
        )
        assert response.status_code == 403
        assert response.get_json()["error"]["code"] == "permission_denied"
