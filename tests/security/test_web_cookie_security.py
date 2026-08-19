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


def _cookie_headers(headers, name: str) -> list[str]:
    return [value for value in headers if value.startswith(f"{name}=")]


def _path(header: str) -> str:
    return next(
        part.split("=", 1)[1]
        for part in header.split("; ")
        if part.startswith("Path=")
    )


def _active_cookie(headers, name: str) -> str:
    return next(
        value
        for value in _cookie_headers(headers, name)
        if "Max-Age=0" not in value
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
    active = {
        name: _active_cookie(headers, name)
        for name in (ACCESS_COOKIE, RENEWAL_COOKIE, DEVICE_COOKIE, CSRF_COOKIE)
    }

    for name in (ACCESS_COOKIE, RENEWAL_COOKIE, DEVICE_COOKIE):
        assert "HttpOnly" in active[name]
        assert "Secure" in active[name]
        assert "SameSite=Lax" in active[name]
    assert "HttpOnly" not in active[CSRF_COOKIE]
    assert "Secure" in active[CSRF_COOKIE]
    assert "SameSite=Lax" in active[CSRF_COOKIE]


def test_csrf_cookie_is_readable_from_the_workspace_page():
    """The SPA can read CSRF while credentials remain confined to browser APIs."""
    app = Flask(__name__)
    with app.test_request_context("/api/web/v1/auth/login", method="POST"):
        response = app.make_response({"ok": True})
        auth._write_session_cookies(response, _cookies(), "device-secret-value")
        cleared = app.make_response({"ok": True})
        auth._clear_session_cookies(cleared)

    written = response.headers.getlist("Set-Cookie")
    written_paths = {
        name: _path(_active_cookie(written, name))
        for name in (ACCESS_COOKIE, RENEWAL_COOKIE, DEVICE_COOKIE, CSRF_COOKIE)
    }

    assert written_paths[CSRF_COOKIE] == "/"
    assert "/workspace".startswith(written_paths[CSRF_COOKIE])

    # The access and device credentials are available only to browser APIs.
    # Account routes need the device binding, while renewal remains narrower.
    assert written_paths[ACCESS_COOKIE] == "/api/web/v1"
    assert written_paths[RENEWAL_COOKIE] == "/api/web/v1/auth"
    assert written_paths[DEVICE_COOKIE] == "/api/web/v1"

    expired = cleared.headers.getlist("Set-Cookie")
    for name in (ACCESS_COOKIE, RENEWAL_COOKIE, CSRF_COOKIE):
        expired_paths = {
            _path(value)
            for value in _cookie_headers(expired, name)
            if "Max-Age=0" in value
        }
        assert written_paths[name] in expired_paths

    # Clear both the current device path and the former renewal-only path so a
    # rollout cannot leave two same-name bindings in a browser cookie jar.
    device_expired_paths = {
        _path(value)
        for value in _cookie_headers(expired, DEVICE_COOKIE)
        if "Max-Age=0" in value
    }
    assert device_expired_paths == {"/api/web/v1", "/api/web/v1/auth"}


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
    renewal = _active_cookie(headers, RENEWAL_COOKIE)
    device = _active_cookie(headers, DEVICE_COOKIE)

    assert "Max-Age" not in renewal
    assert "Expires" not in renewal
    assert "Max-Age" not in device
    assert "Expires" not in device
    assert _path(device) == "/api/web/v1"


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
    assert profile["must_change_pin"] is False
    assert "access-secret" not in serialized
    assert "renewal-secret" not in serialized
    assert "csrf-public" not in serialized
    assert {
        "pin",
        "current_pin",
        "temporary_pin",
        "access_token",
        "renewal_token",
        "csrf_token",
    }.isdisjoint(profile)
