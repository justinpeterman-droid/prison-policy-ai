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


def test_workspace_route_bypasses_legacy_shared_code_gate(monkeypatch):
    response = configured_app(monkeypatch).test_client().get("/workspace")

    assert response.status_code == 503
    assert "Guided Operations preview has not been built." in response.get_data(
        as_text=True
    )


def test_workspace_client_route_returns_spa_fallback(monkeypatch):
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


def test_disabled_identity_api_does_not_register_browser_api(monkeypatch):
    monkeypatch.setattr(app_mod, "ACCESS_CODE", "legacy-user")
    monkeypatch.setenv("ACCESS_API_ENABLED", "false")

    response = app_mod.create_app().test_client().get(
        "/api/web/v1/auth/session",
        headers={"X-Client-Version": "0.1.0"},
    )

    assert response.status_code == 404
