from datetime import UTC, datetime

from backend.persistence.models.identity import StaffMember
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
        device_id="device-fictional-admin-accounts",
        now=datetime.now(UTC),
    )
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        account,
        session_id=tokens.session_id,
        device_id="device-fictional-admin-accounts",
    )
    response = api_client.post(
        "/api/web/v1/admin/elevation",
        json={"pin": "Q7W9E2"},
        headers=browser_headers("request-admin-accounts-elevation"),
    )
    assert response.status_code == 200, response.get_json()


def _step_up(api_client, purpose: str, request_id: str):
    response = api_client.post(
        "/api/web/v1/admin/step-up",
        json={"pin": "Q7W9E2", "purpose": purpose},
        headers=browser_headers(request_id),
    )
    assert response.status_code == 200, response.get_json()
    assert "token" not in repr(response.get_json()).lower()


def _staff_without_account(db_session, employee_number="TEST-7201"):
    now = datetime.now(UTC)
    staff = StaffMember(
        employee_number=employee_number,
        rank="Officer",
        first_name="Riley",
        last_name="Carter",
        shift="C",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(staff)
    db_session.flush()
    return staff


def test_admin_staff_account_create_and_reset_keep_temporary_pin_one_time(
    api_client,
    db_session,
    db_session_factory,
    fictional_staff_and_accounts,
    monkeypatch,
):
    accounts = fictional_staff_and_accounts
    staff = _staff_without_account(db_session)
    staff_id = staff.id
    db_session.commit()
    _authenticate_and_elevate(
        monkeypatch, api_client, db_session, db_session_factory, accounts.admin,
    )

    listed = api_client.get(
        "/api/web/v1/admin/staff?query=TEST-7201",
        headers=browser_headers("request-admin-staff-list"),
    )
    assert listed.status_code == 200, listed.get_json()
    items = listed.get_json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["staff_id"] == str(staff_id)
    assert items[0]["is_active"] is True
    assert items[0]["account"] is None

    denied = api_client.post(
        "/api/web/v1/admin/accounts",
        json={"staff_id": str(staff_id), "role": "user"},
        headers=browser_headers(
            "request-admin-account-create-denied",
            idempotency_key="idem-browser-account-create-0001",
        ),
    )
    assert denied.status_code == 403
    assert denied.get_json()["error"]["code"] == "step_up_required"

    _step_up(api_client, "account_create", "request-admin-account-create-stepup")
    created = api_client.post(
        "/api/web/v1/admin/accounts",
        json={"staff_id": str(staff_id), "role": "user"},
        headers=browser_headers(
            "request-admin-account-create",
            idempotency_key="idem-browser-account-create-0001",
        ),
    )
    assert created.status_code == 200, created.get_json()
    create_data = created.get_json()["data"]
    account_id = create_data["account_id"]
    assert create_data["temporary_pin"]
    assert create_data["temporary_pin_expires_at"]
    serialized = repr(created.get_json()).lower()
    assert "pin_hash" not in serialized
    assert "access_token" not in serialized

    _step_up(api_client, "account_create", "request-admin-account-create-replay-stepup")
    replay = api_client.post(
        "/api/web/v1/admin/accounts",
        json={"staff_id": str(staff_id), "role": "user"},
        headers=browser_headers(
            "request-admin-account-create-replay",
            idempotency_key="idem-browser-account-create-0001",
        ),
    )
    assert replay.status_code == 409
    assert replay.get_json()["error"]["code"] == "idempotent_response_unavailable"
    assert "temporary_pin" not in repr(replay.get_json()).lower()

    accounts_response = api_client.get(
        "/api/web/v1/admin/accounts",
        headers=browser_headers("request-admin-account-list"),
    )
    assert accounts_response.status_code == 200, accounts_response.get_json()
    account = next(
        item for item in accounts_response.get_json()["data"]["items"]
        if item["account_id"] == account_id
    )
    assert account["staff_id"] == str(staff_id)
    assert account["must_change_pin"] is True
    safe_serialized = repr(account).lower()
    assert "pin_hash" not in safe_serialized
    assert "temporary_pin" not in safe_serialized

    _step_up(api_client, "account_reset_pin", "request-admin-account-reset-stepup")
    reset = api_client.post(
        f"/api/web/v1/admin/accounts/{account_id}/reset-pin",
        headers=browser_headers(
            "request-admin-account-reset",
            idempotency_key="idem-browser-account-reset-0001",
        ),
    )
    assert reset.status_code == 200, reset.get_json()
    assert reset.get_json()["data"]["temporary_pin"]

    _step_up(api_client, "account_reset_pin", "request-admin-account-reset-replay-stepup")
    reset_replay = api_client.post(
        f"/api/web/v1/admin/accounts/{account_id}/reset-pin",
        headers=browser_headers(
            "request-admin-account-reset-replay",
            idempotency_key="idem-browser-account-reset-0001",
        ),
    )
    assert reset_replay.status_code == 409
    assert reset_replay.get_json()["error"]["code"] == "idempotent_response_unavailable"
    assert "temporary_pin" not in repr(reset_replay.get_json()).lower()


def test_admin_staff_correction_sessions_unlock_and_last_admin_protection(
    api_client,
    db_session,
    db_session_factory,
    fictional_staff_and_accounts,
    monkeypatch,
):
    accounts = fictional_staff_and_accounts
    user = accounts.user
    first = issue_fictional_tokens(
        db_session,
        account=user,
        device_id="device-fictional-managed-user-1",
        now=datetime.now(UTC),
    )
    second = issue_fictional_tokens(
        db_session,
        account=user,
        device_id="device-fictional-managed-user-2",
        now=datetime.now(UTC),
    )
    user.status = "locked"
    user.failed_attempts = 5
    user.lock_cycle = 1
    db_session.commit()

    _authenticate_and_elevate(
        monkeypatch, api_client, db_session, db_session_factory, accounts.admin,
    )

    _step_up(api_client, "staff_write", "request-admin-staff-create-stepup")
    created_staff = api_client.post(
        "/api/web/v1/admin/staff",
        json={
            "employee_number": "TEST-7301",
            "rank": "Sergeant",
            "first_name": "Morgan",
            "last_name": "Lee",
            "shift": "B",
        },
        headers=browser_headers(
            "request-admin-staff-create",
            idempotency_key="idem-browser-staff-create-0001",
        ),
    )
    assert created_staff.status_code == 200, created_staff.get_json()
    staff_id = created_staff.get_json()["data"]["staff_id"]

    _step_up(api_client, "staff_write", "request-admin-staff-correct-stepup")
    corrected = api_client.patch(
        f"/api/web/v1/admin/staff/{staff_id}",
        json={"shift": "C", "is_active": False},
        headers=browser_headers(
            "request-admin-staff-correct",
            idempotency_key="idem-browser-staff-correct-0001",
        ),
    )
    assert corrected.status_code == 200, corrected.get_json()
    assert corrected.get_json()["data"]["staff_id"] == staff_id
    assert corrected.get_json()["data"]["shift"] == "C"
    assert corrected.get_json()["data"]["is_active"] is False

    sessions = api_client.get(
        f"/api/web/v1/admin/accounts/{user.id}/sessions",
        headers=browser_headers("request-admin-managed-sessions"),
    )
    assert sessions.status_code == 200, sessions.get_json()
    session_ids = {item["session_id"] for item in sessions.get_json()["data"]["items"]}
    assert str(first.session_id) in session_ids
    assert str(second.session_id) in session_ids
    assert "access_token" not in repr(sessions.get_json()).lower()
    assert "renewal_token" not in repr(sessions.get_json()).lower()

    _step_up(api_client, "account_revoke_sessions", "request-admin-revoke-sessions-stepup")
    revoked = api_client.post(
        f"/api/web/v1/admin/accounts/{user.id}/revoke-sessions",
        json={"scope": "all"},
        headers=browser_headers(
            "request-admin-revoke-sessions",
            idempotency_key="idem-browser-revoke-sessions-0001",
        ),
    )
    assert revoked.status_code == 200, revoked.get_json()
    assert revoked.get_json()["data"]["revoked_count"] >= 2

    _step_up(api_client, "account_unlock", "request-admin-unlock-stepup")
    unlocked = api_client.post(
        f"/api/web/v1/admin/accounts/{user.id}/unlock",
        headers=browser_headers(
            "request-admin-unlock",
            idempotency_key="idem-browser-account-unlock-0001",
        ),
    )
    assert unlocked.status_code == 200, unlocked.get_json()
    assert unlocked.get_json()["data"]["status"] == "active"

    _step_up(api_client, "account_role_status", "request-admin-last-admin-stepup")
    last_admin = api_client.patch(
        f"/api/web/v1/admin/accounts/{accounts.admin.id}",
        json={"role": "user", "status": "active"},
        headers=browser_headers(
            "request-admin-last-admin",
            idempotency_key="idem-browser-last-admin-0001",
        ),
    )
    assert last_admin.status_code == 409
    assert last_admin.get_json()["error"]["code"] == "last_active_admin"


def test_regular_user_cannot_discover_accounts_and_staff_admin_routes(
    api_client,
    db_session,
    db_session_factory,
    fictional_user_account,
    monkeypatch,
):
    tokens = issue_fictional_tokens(
        db_session,
        account=fictional_user_account,
        device_id="device-fictional-user-admin-accounts",
        now=datetime.now(UTC),
    )
    db_session.commit()
    authenticate_browser(
        monkeypatch,
        api_client,
        db_session_factory,
        fictional_user_account,
        session_id=tokens.session_id,
        device_id="device-fictional-user-admin-accounts",
    )

    for path in ("/api/web/v1/admin/staff", "/api/web/v1/admin/accounts"):
        response = api_client.get(
            path,
            headers=browser_headers("request-user-admin-accounts-denied"),
        )
        assert response.status_code == 403
        assert response.get_json()["error"]["code"] == "permission_denied"
