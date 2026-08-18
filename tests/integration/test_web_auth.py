from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from flask import Flask

from backend.webapp.web_api import auth, web_api_bp
from backend.webapp.web_api.middleware import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    DEVICE_COOKIE,
    RENEWAL_COOKIE,
)


class FakeDb:
    def __init__(self, account, staff):
        self.account = account
        self.staff = staff
        self.added = []

    def get(self, model, key):
        if key == self.account.id:
            return self.account
        if key == self.staff.id:
            return self.staff
        return None

    def add(self, value):
        self.added.append(value)

    def rollback(self):
        return None


@contextmanager
def fake_scope(db):
    yield db


def _app():
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        IDENTITY_SETTINGS=SimpleNamespace(identity_hash_pepper="pepper"),
        AUDIT_WRITER=object(),
        AUTH_RATE_LIMITS_ENABLED=False,
    )
    app.register_blueprint(web_api_bp)
    return app


def test_session_probe_is_safe_before_sign_in():
    response = _app().test_client().get("/api/web/v1/auth/session")

    assert response.status_code == 200
    assert response.get_json()["data"] == {"authenticated": False, "profile": None}


def test_login_sets_secure_cookies_and_returns_profile_without_tokens(monkeypatch):
    account_id = uuid4()
    staff_id = uuid4()
    session_id = uuid4()
    account = SimpleNamespace(
        id=account_id,
        role="user",
        must_change_pin=False,
    )
    staff = SimpleNamespace(
        id=staff_id,
        employee_number="F-1001",
        rank="Officer",
        first_name="Casey",
        last_name="Morgan",
        shift="A",
    )
    db = FakeDb(account, staff)
    now = datetime.now(UTC)
    actor = SimpleNamespace(
        account_id=account_id,
        staff_member_id=staff_id,
        session_id=session_id,
    )
    cookie_pair = SimpleNamespace(
        access_token="access-secret-value",
        renewal_token="renewal-secret-value",
        csrf_token="csrf-public-value",
        access_expires_at=now + timedelta(minutes=15),
        renewal_expires_at=now + timedelta(days=30),
        persistent=True,
    )
    monkeypatch.setattr(auth, "session_scope", lambda: fake_scope(db))
    monkeypatch.setattr(auth, "_consume_login_limits", lambda *args, **kwargs: None)
    monkeypatch.setattr(auth, "issue_credential", lambda: SimpleNamespace(raw="device-secret-value"))
    monkeypatch.setattr(
        auth,
        "create_browser_session",
        lambda *args, **kwargs: (actor, cookie_pair),
    )

    response = _app().test_client().post(
        "/api/web/v1/auth/login",
        json={"employee_number": "F-1001", "pin": "1234", "persistent": True},
        headers={
            "Origin": "https://example.test",
            "Sec-Fetch-Site": "same-origin",
            "X-Forwarded-Proto": "https",
            "X-Client-Version": "0.1.0",
            "Host": "example.test",
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["authenticated"] is True
    assert body["data"]["profile"]["display_name"] == "Officer Casey Morgan"
    serialized = response.get_data(as_text=True)
    assert "access-secret-value" not in serialized
    assert "renewal-secret-value" not in serialized
    assert "csrf-public-value" not in serialized
    headers = response.headers.getlist("Set-Cookie")
    assert any(value.startswith(f"{ACCESS_COOKIE}=") for value in headers)
    assert any(value.startswith(f"{RENEWAL_COOKIE}=") for value in headers)
    assert any(value.startswith(f"{DEVICE_COOKIE}=") for value in headers)
    assert any(value.startswith(f"{CSRF_COOKIE}=") for value in headers)


def test_login_rejects_cross_site_request_before_authentication(monkeypatch):
    called = []
    monkeypatch.setattr(auth, "create_browser_session", lambda *args, **kwargs: called.append(True))

    response = _app().test_client().post(
        "/api/web/v1/auth/login",
        json={"employee_number": "F-1001", "pin": "1234", "persistent": False},
        headers={
            "Origin": "https://attacker.test",
            "Sec-Fetch-Site": "cross-site",
            "Host": "example.test",
            "X-Forwarded-Proto": "https",
        },
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "csrf_validation_failed"
    assert called == []
