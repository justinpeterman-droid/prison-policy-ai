from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from flask import Flask

from backend.webapp.web_api import auth
from backend.webapp.web_api.middleware import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    DEVICE_COOKIE,
    RENEWAL_COOKIE,
)


def _cookies(*, persistent=True):
    now = datetime.now(UTC)
    return SimpleNamespace(
        access_token="access-secret-value",
        renewal_token="renewal-secret-value",
        csrf_token="csrf-public-value",
        access_expires_at=now + timedelta(minutes=15),
        renewal_expires_at=now + timedelta(days=30),
        persistent=persistent,
    )


def test_session_cookie_writer_keeps_identity_tokens_http_only():
    app = Flask(__name__)
    with app.test_request_context(
        "/api/web/v1/auth/login",
        method="POST",
        headers={"Host": "example.test", "X-Forwarded-Proto": "https"},
    ):
        response = app.make_response({"ok": True})
        auth._write_session_cookies(response, _cookies(), "device-secret-value")

    headers = response.headers.getlist("Set-Cookie")
    by_name = {header.split("=", 1)[0]: header for header in headers}

    assert {ACCESS_COOKIE, RENEWAL_COOKIE, DEVICE_COOKIE, CSRF_COOKIE} <= set(by_name)
    for name in (ACCESS_COOKIE, RENEWAL_COOKIE, DEVICE_COOKIE):
        assert "HttpOnly" in by_name[name]
        assert "Secure" in by_name[name]
        assert "SameSite=Lax" in by_name[name]
    assert "HttpOnly" not in by_name[CSRF_COOKIE]
    assert "Secure" in by_name[CSRF_COOKIE]
    assert "SameSite=Lax" in by_name[CSRF_COOKIE]


def test_nonpersistent_renewal_cookie_is_a_browser_session_cookie():
    app = Flask(__name__)
    with app.test_request_context(
        "/api/web/v1/auth/login",
        method="POST",
        headers={"Host": "localhost"},
    ):
        response = app.make_response({"ok": True})
        auth._write_session_cookies(response, _cookies(persistent=False), "device-secret-value")

    headers = response.headers.getlist("Set-Cookie")
    renewal = next(value for value in headers if value.startswith(f"{RENEWAL_COOKIE}="))
    device = next(value for value in headers if value.startswith(f"{DEVICE_COOKIE}="))

    assert "Max-Age" not in renewal
    assert "Expires" not in renewal
    assert "Max-Age" not in device
    assert "Expires" not in device


def test_safe_profile_shape_contains_no_identity_credentials():
    account_id = uuid4()
    staff_id = uuid4()
    session_id = uuid4()
    db = SimpleNamespace(
        get=lambda model, key: (
            SimpleNamespace(
                id=account_id,
                role="user",
                must_change_pin=False,
            )
            if key == account_id
            else SimpleNamespace(
                id=staff_id,
                employee_number="F-1001",
                rank="Officer",
                first_name="Casey",
                last_name="Morgan",
                shift="A",
            )
        )
    )
    actor = SimpleNamespace(
        account_id=account_id,
        staff_member_id=staff_id,
        session_id=session_id,
    )

    profile = auth._profile(db, actor)

    serialized = repr(profile)
    assert profile["employee_number"] == "F-1001"
    assert "access-secret" not in serialized
    assert "renewal-secret" not in serialized
    assert "csrf-public" not in serialized
    assert "pin" not in serialized.lower()
