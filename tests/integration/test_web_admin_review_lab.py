from datetime import UTC, datetime

from backend.identity.tokens import hash_token
from backend.persistence.models.security import BrowserHandoff
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
        device_id="device-fictional-admin-review-lab",
        now=datetime.now(UTC),
    )
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        account,
        session_id=tokens.session_id,
        device_id="device-fictional-admin-review-lab",
    )
    elevated = api_client.post(
        "/api/web/v1/admin/elevation",
        json={"pin": "Q7W9E2"},
        headers=browser_headers("request-admin-review-lab-elevation"),
    )
    assert elevated.status_code == 200, elevated.get_json()


def test_admin_review_lab_handoff_is_one_use_short_lived_and_fragment_scoped(
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

    denied = api_client.post(
        "/api/web/v1/admin/review-lab-handoffs",
        headers=browser_headers("request-admin-review-lab-no-stepup"),
    )
    assert denied.status_code == 403
    assert denied.get_json()["error"]["code"] == "step_up_required"

    step_up = api_client.post(
        "/api/web/v1/admin/step-up",
        json={"pin": "Q7W9E2", "purpose": "review_lab_handoff"},
        headers=browser_headers("request-admin-review-lab-stepup"),
    )
    assert step_up.status_code == 200, step_up.get_json()
    assert "token" not in repr(step_up.get_json()).lower()

    issued = api_client.post(
        "/api/web/v1/admin/review-lab-handoffs",
        headers=browser_headers("request-admin-review-lab-issue"),
    )
    assert issued.status_code == 200, issued.get_json()
    data = issued.get_json()["data"]
    assert set(data) == {"url", "expires_at"}
    assert data["url"].startswith("/access-handoff#")
    token = data["url"].split("#", 1)[1]
    assert len(token) >= 40
    serialized = repr(data).lower()
    for forbidden in (
        "access_token",
        "renewal_token",
        "csrf_token",
        "q7w9e2",
        "shared_admin",
        "access_code",
    ):
        assert forbidden not in serialized

    with db_session_factory() as session:
        stored = session.query(BrowserHandoff).one()
        assert stored.token_hash == hash_token(token)
        lifetime = (stored.expires_at - stored.created_at).total_seconds()
        assert 0 < lifetime <= 60

    redeemed = api_client.post(
        "/api/browser-handoffs/redeem",
        json={"token": token},
    )
    assert redeemed.status_code == 200, redeemed.get_json()
    assert redeemed.get_json()["data"] == {"redeemed": True}
    assert any(
        header.startswith("review_session=") and "HttpOnly" in header
        for header in redeemed.headers.getlist("Set-Cookie")
    )

    replay = api_client.post(
        "/api/browser-handoffs/redeem",
        json={"token": token},
    )
    assert replay.status_code == 401
    assert replay.get_json()["error"]["code"] == "handoff_invalid"


def test_regular_user_cannot_issue_review_lab_handoff(
    api_client,
    db_session,
    db_session_factory,
    fictional_user_account,
    monkeypatch,
):
    tokens = issue_fictional_tokens(
        db_session,
        account=fictional_user_account,
        device_id="device-fictional-user-review-lab",
        now=datetime.now(UTC),
    )
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        fictional_user_account,
        session_id=tokens.session_id,
        device_id="device-fictional-user-review-lab",
    )

    response = api_client.post(
        "/api/web/v1/admin/review-lab-handoffs",
        headers=browser_headers("request-user-review-lab-denied"),
    )
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "permission_denied"
