from contextlib import contextmanager

from backend.webapp import app as app_mod
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.routes import web_app
from backend.webapp.web_api import auth as web_auth


def configured_app(monkeypatch):
    monkeypatch.setattr(app_mod, "ACCESS_CODE", "legacy-user")
    monkeypatch.setattr(app_mod, "ADMIN_CODE", "legacy-admin")
    monkeypatch.setenv("ACCESS_API_ENABLED", "true")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://app:test@localhost/access_test"
    )
    monkeypatch.setenv("IDENTITY_HASH_PEPPER", "p" * 32)
    monkeypatch.setenv("CURSOR_SIGNING_KEY", "c" * 32)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://review.example.gov")
    return app_mod.create_app()


def test_workspace_route_bypasses_legacy_shared_code_gate(monkeypatch, tmp_path):
    monkeypatch.setattr(web_app, "_web_root", lambda: tmp_path / "missing-web")
    response = configured_app(monkeypatch).test_client().get("/workspace")

    assert response.status_code == 503
    assert "Guided Operations preview has not been built." in response.get_data(
        as_text=True
    )


def test_workspace_client_route_returns_spa_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(web_app, "_web_root", lambda: tmp_path / "missing-web")
    response = configured_app(monkeypatch).test_client().get(
        "/workspace/reports/00000000-0000-4000-8000-000000000001"
    )

    assert response.status_code == 503
    assert "Guided Operations preview has not been built." in response.get_data(
        as_text=True
    )


def test_browser_session_api_is_registered_without_legacy_auth(monkeypatch):
    client = configured_app(monkeypatch).test_client()
    client.set_cookie("access_code", "legacy-admin")

    response = client.get(
        "/api/web/v1/auth/session",
        headers={"X-Client-Version": "0.1.0"},
    )

    assert response.status_code == 200
    assert response.get_json()["data"] == {
        "authenticated": False,
        "profile": None,
    }


def test_incident_library_api_is_registered_and_requires_individual_auth(monkeypatch):
    response = configured_app(monkeypatch).test_client().get(
        "/api/web/v1/incidents",
        headers={"X-Client-Version": "0.1.0"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "authentication_required"


def test_throttled_login_reports_rate_limiting_not_an_internal_error(monkeypatch):
    """A throttled officer must be told to wait, not that the service broke.

    `_consume_login_limits` signals throttling with ApiError, which none of the
    login route's except clauses name — without a blueprint handler for it the
    catch-all turns a deliberate 429 into a 500 with no Retry-After.
    """
    app = configured_app(monkeypatch)
    app.config["AUDIT_WRITER"] = lambda *args, **kwargs: None

    @contextmanager
    def fake_scope():
        yield object()

    monkeypatch.setattr(web_auth, "session_scope", fake_scope)

    def throttle(*args, **kwargs):
        raise ApiError(
            "rate_limited",
            "Too many authentication attempts.",
            status=429,
            retryable=True,
            details={"retry_after_seconds": 42},
        )

    monkeypatch.setattr(web_auth, "_consume_login_limits", throttle)

    response = app.test_client().post(
        "/api/web/v1/auth/login",
        json={"employee_number": "F-1001", "pin": "1234", "persistent": False},
        headers={"Origin": "http://localhost", "X-Client-Version": "0.1.0"},
    )

    assert response.status_code == 429
    assert response.get_json()["error"]["code"] == "rate_limited"
    assert response.get_json()["error"]["retryable"] is True
    assert response.headers["Retry-After"] == "42"


def test_disabled_identity_api_does_not_register_browser_api(monkeypatch):
    monkeypatch.setattr(app_mod, "ACCESS_CODE", "legacy-user")
    monkeypatch.setenv("ACCESS_API_ENABLED", "false")

    response = app_mod.create_app().test_client().get(
        "/api/web/v1/auth/session",
        headers={"X-Client-Version": "0.1.0"},
    )

    assert response.status_code == 404
