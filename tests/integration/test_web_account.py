from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from backend.identity.pins import verify_pin
from backend.persistence.models.identity import Account
from backend.persistence.models.security import AuditEvent
from backend.persistence.models.sessions import AccessSession
from tests.integration.identity_fixtures import issue_fictional_tokens
from tests.support.web_browser import authenticate_browser, browser_headers


CURRENT_DEVICE = "device-fictional-owner-0001"
OTHER_DEVICE = "device-fictional-owner-0002"


def _authenticate(
    monkeypatch,
    api_client,
    db_session_factory,
    account,
    token_pair,
    *,
    device_id=CURRENT_DEVICE,
):
    return authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        account,
        session_id=token_pair.session_id,
        device_id=device_id,
    )


def test_account_lists_only_safe_session_metadata_and_revokes_another_device(
    api_client,
    db_session,
    db_session_factory,
    fictional_staff_and_accounts,
    fictional_owner_tokens,
    identity_fixed_now,
    monkeypatch,
):
    account = fictional_staff_and_accounts.user
    other = issue_fictional_tokens(
        db_session,
        account=account,
        device_id=OTHER_DEVICE,
        now=identity_fixed_now + timedelta(minutes=1),
    )
    db_session.commit()
    _authenticate(
        monkeypatch,
        api_client,
        db_session_factory,
        account,
        fictional_owner_tokens,
    )

    listed = api_client.get(
        "/api/web/v1/account/sessions",
        headers=browser_headers("request_account_sessions_list"),
    )

    assert listed.status_code == 200, listed.get_json()
    data = listed.get_json()["data"]
    assert {item["session_id"] for item in data["items"]} == {
        str(fictional_owner_tokens.session_id),
        str(other.session_id),
    }
    current = next(
        item for item in data["items"]
        if item["session_id"] == str(fictional_owner_tokens.session_id)
    )
    assert current["current"] is True
    serialized = repr(data)
    for forbidden in ("access_token", "renewal_token", "csrf_token", "pin_hash"):
        assert forbidden not in serialized

    revoked = api_client.delete(
        f"/api/web/v1/account/sessions/{other.session_id}",
        headers=browser_headers("request_account_session_revoke"),
    )
    assert revoked.status_code == 200, revoked.get_json()
    assert revoked.get_json()["data"] == {
        "session_id": str(other.session_id),
        "revoked": True,
    }

    with db_session_factory() as session:
        row = session.get(AccessSession, other.session_id)
        assert row is not None
        assert row.revoked_at is not None


def test_account_changes_pin_rotates_opaque_cookies_and_revokes_other_sessions(
    api_client,
    db_session,
    db_session_factory,
    fictional_staff_and_accounts,
    monkeypatch,
):
    account = fictional_staff_and_accounts.user
    fixed_now = datetime.now(UTC)
    current = issue_fictional_tokens(
        db_session,
        account=account,
        device_id=CURRENT_DEVICE,
        now=fixed_now,
    )
    other = issue_fictional_tokens(
        db_session,
        account=account,
        device_id=OTHER_DEVICE,
        now=fixed_now + timedelta(minutes=1),
    )
    db_session.commit()
    _authenticate(
        monkeypatch,
        api_client,
        db_session_factory,
        account,
        current,
    )

    changed = api_client.post(
        "/api/web/v1/account/change-pin",
        json={"current_pin": "Q7W9E2", "new_pin": "A1B2C3"},
        headers=browser_headers("request_account_pin_change"),
    )

    assert changed.status_code == 200, changed.get_json()
    assert changed.get_json()["data"]["changed"] is True
    assert changed.get_json()["data"]["must_change_pin"] is False
    serialized = repr(changed.get_json())
    for forbidden in ("Q7W9E2", "A1B2C3", "access_token", "renewal_token"):
        assert forbidden not in serialized
    cookie_headers = changed.headers.getlist("Set-Cookie")
    assert any(header.startswith("slut_web_access=") and "HttpOnly" in header for header in cookie_headers)
    assert any(header.startswith("slut_web_renewal=") and "HttpOnly" in header for header in cookie_headers)

    with db_session_factory() as session:
        refreshed = session.get(Account, account.id)
        assert refreshed is not None
        assert verify_pin(refreshed.pin_hash, "A1B2C3") is True
        other_row = session.get(AccessSession, other.session_id)
        assert other_row is not None
        assert other_row.revoked_at is not None
        event = session.scalar(select(AuditEvent).where(
            AuditEvent.action == "auth.pin_changed",
            AuditEvent.actor_account_id == account.id,
        ))
        assert event is not None
        assert "A1B2C3" not in repr(event.details)
        assert "Q7W9E2" not in repr(event.details)


def test_account_rejects_cross_site_or_malformed_security_writes(
    api_client,
    db_session,
    db_session_factory,
    fictional_staff_and_accounts,
    fictional_owner_tokens,
    monkeypatch,
):
    account = fictional_staff_and_accounts.user
    db_session.commit()
    _authenticate(
        monkeypatch,
        api_client,
        db_session_factory,
        account,
        fictional_owner_tokens,
    )

    malformed = api_client.post(
        "/api/web/v1/account/change-pin",
        json={
            "current_pin": "Q7W9E2",
            "new_pin": "A1B2C3",
            "temporary_pin": "forbidden",
        },
        headers=browser_headers("request_account_pin_malformed"),
    )
    assert malformed.status_code == 400
    assert malformed.get_json()["error"]["code"] == "validation_failed"

    headers = browser_headers("request_account_pin_cross_site")
    headers["Origin"] = "https://attacker.invalid"
    headers["Sec-Fetch-Site"] = "cross-site"
    cross_site = api_client.post(
        "/api/web/v1/account/change-pin",
        json={"current_pin": "Q7W9E2", "new_pin": "A1B2C3"},
        headers=headers,
    )
    assert cross_site.status_code == 403
    assert cross_site.get_json()["error"]["code"] == "csrf_validation_failed"
