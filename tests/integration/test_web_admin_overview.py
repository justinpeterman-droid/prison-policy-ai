from datetime import UTC, datetime

from tests.integration.identity_fixtures import issue_fictional_tokens
from tests.support.web_browser import authenticate_browser, browser_headers


def _elevated_admin(
    monkeypatch,
    api_client,
    db_session,
    db_session_factory,
    fictional_admin_account,
):
    tokens = issue_fictional_tokens(
        db_session,
        account=fictional_admin_account,
        device_id="device-fictional-admin-overview",
        now=datetime.now(UTC),
    )
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        fictional_admin_account,
        session_id=tokens.session_id,
        device_id="device-fictional-admin-overview",
    )
    response = api_client.post(
        "/api/web/v1/admin/elevation",
        json={"pin": "Q7W9E2"},
        headers=browser_headers("request-admin-overview-elevation"),
    )
    assert response.status_code == 200, response.get_json()


def test_admin_overview_requires_elevation_and_returns_bounded_safe_shape(
    api_client,
    db_session,
    db_session_factory,
    fictional_admin_account,
    monkeypatch,
):
    tokens = issue_fictional_tokens(
        db_session,
        account=fictional_admin_account,
        device_id="device-fictional-admin-overview-locked",
        now=datetime.now(UTC),
    )
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        fictional_admin_account,
        session_id=tokens.session_id,
        device_id="device-fictional-admin-overview-locked",
    )

    denied = api_client.get(
        "/api/web/v1/admin/overview",
        headers=browser_headers("request-admin-overview-denied"),
    )
    assert denied.status_code == 403
    assert denied.get_json()["error"]["code"] == "admin_elevation_required"

    elevated = api_client.post(
        "/api/web/v1/admin/elevation",
        json={"pin": "Q7W9E2"},
        headers=browser_headers("request-admin-overview-elevate"),
    )
    assert elevated.status_code == 200, elevated.get_json()

    response = api_client.get(
        "/api/web/v1/admin/overview",
        headers=browser_headers("request-admin-overview"),
    )
    assert response.status_code == 200, response.get_json()
    data = response.get_json()["data"]
    assert set(data) == {
        "todays_paperwork",
        "incidents_needing_attention",
        "account_conditions",
        "system_availability",
        "recent_administrative_activity",
    }
    assert data["todays_paperwork"]["assignment_roster"]["status"] == "not_started"
    assert data["todays_paperwork"]["uniform_inspection"]["status"] == "not_started"
    assert len(data["incidents_needing_attention"]) <= 10
    assert len(data["recent_administrative_activity"]) <= 10
    assert set(data["account_conditions"]) == {
        "locked",
        "deactivated",
        "temporary_pin",
    }
    assert data["account_conditions"]["temporary_pin"] >= 1
    assert set(data["system_availability"]) >= {"database", "queue", "ai", "policy_expert"}
    assert set(data["system_availability"].values()) <= {
        "Operational",
        "Degraded",
        "Unavailable",
    }

    serialized = repr(data).lower()
    for forbidden in (
        "pin_hash",
        "temporary_pin_expires_at",
        "access_token",
        "renewal_token",
        "csrf_token",
        "narrative",
        "field_notes",
        "current_payload",
        "traceback",
    ):
        assert forbidden not in serialized
