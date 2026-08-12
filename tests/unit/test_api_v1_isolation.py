from backend.webapp import app as app_mod


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


def test_legacy_cookie_cannot_authenticate_api_v1(monkeypatch):
    client = configured_app(monkeypatch).test_client()
    client.set_cookie("access_code", "legacy-admin")
    response = client.get("/api/v1/me", headers={"X-Client-Version": "1.0.0"})
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "authentication_required"


def test_bearer_header_does_not_authenticate_legacy_page(monkeypatch):
    client = configured_app(monkeypatch).test_client()
    response = client.get(
        "/reports", headers={"Authorization": "Bearer fake-access-token"}
    )
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


def test_disabled_access_api_is_not_registered(monkeypatch):
    monkeypatch.setattr(app_mod, "ACCESS_CODE", "legacy-user")
    monkeypatch.setenv("ACCESS_API_ENABLED", "false")
    response = app_mod.create_app().test_client().get("/api/v1/client-policy")
    assert response.status_code == 404
