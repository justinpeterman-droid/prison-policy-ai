"""RP-10 legacy browser-report rollout control."""
import pytest


@pytest.fixture
def legacy_client(monkeypatch):
    import backend.webapp.app as app_module

    monkeypatch.setattr(app_module, "ACCESS_CODE", "fictional-legacy-code")
    monkeypatch.setenv("ACCESS_API_ENABLED", "true")
    monkeypatch.setenv("IDENTITY_HASH_PEPPER", "p" * 32)
    monkeypatch.setenv("CURSOR_SIGNING_KEY", "c" * 32)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://integration.example.invalid")
    monkeypatch.setenv("LEGACY_REPORT_MODE", "restricted")
    client = app_module.create_app().test_client()
    client.set_cookie("access_code", "fictional-legacy-code")
    return client


@pytest.mark.parametrize("path", [
    "/api/reports/classify", "/api/reports/extract", "/api/reports/generate",
    "/api/reports/disciplinary", "/api/reports/download",
])
def test_restricted_legacy_actions_return_safe_maintenance(legacy_client, path):
    response = legacy_client.post(path, json={"notes": "fictional marker"})
    assert response.status_code == 503
    assert response.get_json()["error"] == (
        "Legacy report actions are temporarily unavailable. Use the Access workspace."
    )


def test_invalid_legacy_mode_fails_startup(monkeypatch):
    import backend.webapp.app as app_module

    monkeypatch.setattr(app_module, "ACCESS_CODE", "fictional-legacy-code")
    monkeypatch.setenv("LEGACY_REPORT_MODE", "unexpected")
    with pytest.raises(RuntimeError, match="LEGACY_REPORT_MODE"):
        app_module.create_app()


def test_pilot_fallback_preserves_transient_legacy_route(monkeypatch):
    import backend.webapp.app as app_module

    monkeypatch.setattr(app_module, "ACCESS_CODE", "fictional-legacy-code")
    monkeypatch.setenv("ACCESS_API_ENABLED", "true")
    monkeypatch.setenv("IDENTITY_HASH_PEPPER", "p" * 32)
    monkeypatch.setenv("CURSOR_SIGNING_KEY", "c" * 32)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://integration.example.invalid")
    monkeypatch.setenv("LEGACY_REPORT_MODE", "pilot_fallback")
    client = app_module.create_app().test_client()
    client.set_cookie("access_code", "fictional-legacy-code")
    response = client.post("/api/reports/extract", json={"notes": ""})
    assert response.status_code == 400
    page = client.get("/")
    assert page.status_code == 200
    assert b'data-legacy-pilot-warning="true"' in page.data
