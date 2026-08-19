from datetime import UTC, datetime

from tests.integration.identity_fixtures import issue_fictional_tokens
from tests.support.web_browser import authenticate_browser, browser_headers


def _authenticate_admin(
    monkeypatch,
    api_client,
    db_session,
    db_session_factory,
    fictional_admin_account,
):
    now = datetime.now(UTC)
    tokens = issue_fictional_tokens(
        db_session,
        account=fictional_admin_account,
        device_id="device-fictional-admin-browser-0001",
        now=now,
    )
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        fictional_admin_account,
        session_id=tokens.session_id,
        device_id="device-fictional-admin-browser-0001",
    )
    return tokens


def test_user_cannot_discover_admin_elevation_state(
    api_client,
    db_session,
    db_session_factory,
    fictional_user_account,
    monkeypatch,
):
    tokens = issue_fictional_tokens(
        db_session,
        account=fictional_user_account,
        device_id="device-fictional-user-admin-denial",
        now=datetime.now(UTC),
    )
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        fictional_user_account,
        session_id=tokens.session_id,
        device_id="device-fictional-user-admin-denial",
    )

    response = api_client.get(
        "/api/web/v1/admin/elevation",
        headers=browser_headers("request-admin-user-denial"),
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "permission_denied"


def test_admin_enters_center_and_reads_safe_elevation_state(
    api_client,
    db_session,
    db_session_factory,
    fictional_admin_account,
    monkeypatch,
):
    _authenticate_admin(
        monkeypatch,
        api_client,
        db_session,
        db_session_factory,
        fictional_admin_account,
    )

    before = api_client.get(
        "/api/web/v1/admin/elevation",
        headers=browser_headers("request-admin-state-before"),
    )
    assert before.status_code == 200, before.get_json()
    assert before.get_json()["data"] == {
        "elevated": False,
        "elevation_expires_at": None,
    }

    elevated = api_client.post(
        "/api/web/v1/admin/elevation",
        json={"pin": "Q7W9E2"},
        headers=browser_headers("request-admin-enter-center"),
    )
    assert elevated.status_code == 200, elevated.get_json()
    data = elevated.get_json()["data"]
    assert data["elevated"] is True
    assert isinstance(data["elevation_expires_at"], str)
    serialized = repr(elevated.get_json()).lower()
    for forbidden in ("q7w9e2", "step_up_token", "token_hash", "pin_hash"):
        assert forbidden not in serialized

    after = api_client.get(
        "/api/web/v1/admin/elevation",
        headers=browser_headers("request-admin-state-after"),
    )
    assert after.status_code == 200, after.get_json()
    assert after.get_json()["data"]["elevated"] is True


def test_admin_step_up_is_http_only_purpose_scoped_and_not_returned_in_json(
    api_client,
    db_session,
    db_session_factory,
    fictional_admin_account,
    monkeypatch,
):
    _authenticate_admin(
        monkeypatch,
        api_client,
        db_session,
        db_session_factory,
        fictional_admin_account,
    )

    response = api_client.post(
        "/api/web/v1/admin/step-up",
        json={"pin": "Q7W9E2", "purpose": "account_reset_pin"},
        headers=browser_headers("request-admin-step-up-web"),
    )

    assert response.status_code == 200, response.get_json()
    data = response.get_json()["data"]
    assert data["purpose"] == "account_reset_pin"
    assert isinstance(data["expires_at"], str)
    serialized = repr(response.get_json()).lower()
    assert "step_up_token" not in serialized
    assert "q7w9e2" not in serialized

    cookie = next(
        value
        for value in response.headers.getlist("Set-Cookie")
        if value.startswith("slut_web_admin_step_up=")
    )
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Path=/api/web/v1/admin" in cookie
    assert "Max-Age=300" in cookie
