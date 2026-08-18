from types import SimpleNamespace
from uuid import uuid4

import pytest
from flask import Flask, g

from backend.identity.browser_sessions import BrowserCsrfInvalid
from backend.webapp.web_api import middleware


def _request_context(app, *, origin="https://example.test", fetch_site="same-origin"):
    headers = {"Host": "example.test", "X-Forwarded-Proto": "https"}
    if origin is not None:
        headers["Origin"] = origin
    if fetch_site is not None:
        headers["Sec-Fetch-Site"] = fetch_site
    return app.test_request_context("/api/web/v1/auth/login", method="POST", headers=headers)


def test_same_origin_validation_accepts_forwarded_https_origin():
    app = Flask(__name__)

    with _request_context(app):
        middleware.validate_same_origin_request()


def test_same_origin_validation_rejects_missing_origin():
    app = Flask(__name__)

    with _request_context(app, origin=None):
        with pytest.raises(BrowserCsrfInvalid):
            middleware.validate_same_origin_request()


def test_same_origin_validation_rejects_cross_site_fetch_and_origin():
    app = Flask(__name__)

    with _request_context(app, origin="https://attacker.test", fetch_site="cross-site"):
        with pytest.raises(BrowserCsrfInvalid):
            middleware.validate_same_origin_request()


def test_csrf_guard_requires_matching_header_cookie_and_session_digest(monkeypatch):
    app = Flask(__name__)
    actor = SimpleNamespace(session_id=uuid4())
    validated = []
    monkeypatch.setattr(
        middleware,
        "validate_browser_csrf",
        lambda db, *, actor, supplied_token: validated.append((db, actor, supplied_token)),
    )

    @app.post("/write")
    @middleware.require_browser_csrf
    def write():
        return {"ok": True}

    client = app.test_client()
    with client:
        client.set_cookie(middleware.CSRF_COOKIE, "csrf-value")
        with app.test_request_context():
            pass
        # The guard reads these values from Flask request context.
        @app.before_request
        def attach_context():
            g.browser_actor = actor
            g.browser_db_session = "db"

        response = client.post(
            "/write",
            headers={
                "Origin": "http://localhost",
                "Sec-Fetch-Site": "same-origin",
                "X-CSRF-Token": "csrf-value",
            },
            base_url="http://localhost",
        )

    assert response.status_code == 200
    assert validated == [("db", actor, "csrf-value")]


def test_csrf_guard_rejects_missing_confirmation():
    app = Flask(__name__)

    @app.before_request
    def attach_context():
        g.browser_actor = SimpleNamespace(session_id=uuid4())
        g.browser_db_session = "db"
        g.request_id = "req-csrf"

    @app.post("/write")
    @middleware.require_browser_csrf
    def write():
        return {"ok": True}

    response = app.test_client().post(
        "/write",
        headers={"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"},
        base_url="http://localhost",
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "csrf_validation_failed"
