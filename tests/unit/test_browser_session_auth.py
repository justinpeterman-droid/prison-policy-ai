from datetime import UTC, datetime, timedelta
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from flask import Flask, g

from backend.identity.browser_handoffs import (
    BrowserSessionResult,
    BrowserSessionInvalid,
    require_review_lab_access,
    resolve_browser_session,
)
from backend.identity.tokens import hash_token


NOW = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)


class FakeSession:
    def __init__(self, *scalars):
        self.scalars = list(scalars)

    def scalar(self, _statement):
        return self.scalars.pop(0)

    def flush(self):
        return None


def _rows(*, role="admin", status="active", staff_active=True, revoked_at=None):
    account_id, staff_id, access_id, browser_id = uuid4(), uuid4(), uuid4(), uuid4()
    browser = SimpleNamespace(
        id=browser_id, account_id=account_id, issuing_session_id=access_id,
        token_hash=hash_token("fictional-browser-cookie"), purpose="review_lab",
        last_used_at=NOW, expires_at=NOW + timedelta(minutes=1),
        revoked_at=revoked_at,
    )
    access = SimpleNamespace(
        id=access_id, account_id=account_id, auth_version=4, revoked_at=None,
        renewal_expires_at=NOW + timedelta(hours=1),
    )
    account = SimpleNamespace(
        id=account_id, staff_member_id=staff_id, role=role, status=status,
        auth_version=4,
    )
    staff = SimpleNamespace(id=staff_id, is_active=staff_active)
    return browser, access, account, staff


def test_browser_session_resolves_attributed_actor_and_slides_idle_expiry():
    browser, _access, account, staff = _rows()
    actor = resolve_browser_session(
        FakeSession(browser, account, staff),
        cookie_value="fictional-browser-cookie", now=NOW,
    )
    assert actor.account_id == account.id
    assert actor.staff_member_id == staff.id
    assert actor.browser_session_id == browser.id
    assert actor.role == "admin"
    assert browser.last_used_at == NOW
    assert browser.expires_at == NOW + timedelta(minutes=30)


@pytest.mark.parametrize(
    "role,status,staff_active",
    [("user", "active", True), ("admin", "deactivated", True), ("admin", "active", False)],
)
def test_browser_session_rejects_non_admin_or_inactive_identity(role, status, staff_active):
    browser, _access, account, staff = _rows(
        role=role, status=status, staff_active=staff_active
    )
    with pytest.raises(BrowserSessionInvalid):
        resolve_browser_session(
            FakeSession(browser, account, staff),
            cookie_value="fictional-browser-cookie", now=NOW,
        )


def test_review_lab_guard_accepts_only_individual_or_marked_legacy_admin():
    app = Flask(__name__)

    @app.get("/review-lab")
    @require_review_lab_access
    def protected():
        return {"kind": g.review_lab_access_kind}

    @app.before_request
    def context():
        if app.config.get("INDIVIDUAL"):
            g.browser_actor = SimpleNamespace(account_id=uuid4())
            g.review_lab_access_kind = "individual_browser_session"
        elif app.config.get("LEGACY"):
            g.review_lab_access_kind = "legacy_shared_admin"

    client = app.test_client()
    assert client.get("/review-lab").status_code == 404
    app.config["LEGACY"] = True
    assert client.get("/review-lab").get_json()["kind"] == "legacy_shared_admin"
    app.config["LEGACY"] = False
    app.config["INDIVIDUAL"] = True
    assert client.get("/review-lab").get_json()["kind"] == "individual_browser_session"


def test_redeem_route_sets_only_a_secure_browser_session_cookie(monkeypatch):
    import backend.webapp.routes.browser_handoffs as routes

    @contextmanager
    def fake_scope():
        yield object()

    monkeypatch.setattr(routes, "session_scope", fake_scope)
    monkeypatch.setattr(
        routes, "redeem_browser_handoff",
        lambda *_args, **_kwargs: BrowserSessionResult(
            uuid4(), "fictional-browser-session-cookie-value-0001",
            NOW + timedelta(minutes=30),
        ),
    )
    app = Flask(__name__, template_folder="../../backend/webapp/templates")
    app.config["AUDIT_WRITER"] = object()
    app.register_blueprint(routes.browser_handoffs_bp)

    response = app.test_client().post(
        "/api/browser-handoffs/redeem",
        json={"token": "fictional-handoff-token-value-that-is-long-enough-0001"},
    )

    assert response.status_code == 200
    cookie = response.headers["Set-Cookie"]
    assert cookie.startswith("review_session=")
    assert "Path=/" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=Lax" in cookie
    assert "Max-Age" not in cookie
    assert "Expires" not in cookie


def test_fragment_landing_has_no_store_and_no_referrer_headers():
    import backend.webapp.routes.browser_handoffs as routes

    app = Flask(
        __name__, template_folder="../../backend/webapp/templates",
        static_folder="../../backend/webapp/static",
    )
    app.register_blueprint(routes.browser_handoffs_bp)
    response = app.test_client().get("/access-handoff")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_identity_enabled_app_does_not_treat_disabled_legacy_gate_as_admin(
    monkeypatch,
):
    from backend.webapp import app as app_module
    from backend.webapp.routes import review_lab as review_routes

    monkeypatch.setattr(app_module, "ACCESS_CODE", "")
    monkeypatch.setattr(app_module, "ADMIN_CODE", "")
    monkeypatch.setattr(review_routes, "REVIEW_LAB_ENABLED", True)
    monkeypatch.setenv("ACCESS_API_ENABLED", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://app:test@localhost/access_test")
    monkeypatch.setenv("IDENTITY_HASH_PEPPER", "p" * 32)
    monkeypatch.setenv("CURSOR_SIGNING_KEY", "c" * 32)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://review.example.gov")

    response = app_module.create_app().test_client().get("/review-lab")
    assert response.status_code == 404
