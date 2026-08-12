from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from openapi_spec_validator import validate
import yaml

from backend.identity.sessions import SessionTokenPair
from backend.webapp import app as app_mod


def _document():
    with open("openapi/access-v1.yaml", encoding="utf-8") as source:
        return yaml.safe_load(source)


def test_auth_openapi_is_valid_public_closed_and_write_only():
    document = _document()
    validate(document)
    for path in ("/api/v1/auth/login", "/api/v1/auth/renew"):
        operation = document["paths"][path]["post"]
        assert operation["security"] == []
        assert {parameter["$ref"] for parameter in operation["parameters"]} >= {
            "#/components/parameters/XClientVersion"
        }
    schemas = document["components"]["schemas"]
    assert schemas["LoginRequest"]["additionalProperties"] is False
    assert schemas["RenewRequest"]["additionalProperties"] is False
    assert schemas["LoginRequest"]["properties"]["pin"]["writeOnly"] is True
    assert schemas["LoginRequest"]["properties"]["device_id"]["writeOnly"] is True
    assert schemas["RenewRequest"]["properties"]["renewal_token"]["writeOnly"] is True
    assert set(schemas["SessionProfile"]["required"]) == {
        "staff_id", "employee_number", "display_name", "rank", "shift", "role", "status"
    }


def _pair():
    now = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
    return SessionTokenPair(
        session_id=uuid4(), access_token="fictional-access-token",
        renewal_token="fictional-renewal-token", access_expires_at=now + timedelta(minutes=15),
        renewal_expires_at=now + timedelta(hours=12), persistent=False,
        requires_pin_change=True,
        profile={
            "staff_id": str(uuid4()), "employee_number": "TEST-1001",
            "display_name": "Officer Avery Morgan", "rank": "Officer", "shift": "A",
            "role": "user", "status": "active",
        },
    )


def configured_client(monkeypatch):
    monkeypatch.setattr(app_mod, "ACCESS_CODE", "legacy-user")
    monkeypatch.setenv("ACCESS_API_ENABLED", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://app:test@localhost/access_test")
    monkeypatch.setenv("IDENTITY_HASH_PEPPER", "p" * 32)
    monkeypatch.setenv("CURSOR_SIGNING_KEY", "c" * 32)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://review.example.gov")
    app = app_mod.create_app()
    app.config["AUDIT_WRITER"] = object()
    return app.test_client()


def test_login_route_returns_profile_without_follow_up_and_rejects_extra_fields(monkeypatch):
    import backend.webapp.api_v1.auth as auth_api

    pair = _pair()

    @contextmanager
    def fake_scope():
        yield object()

    monkeypatch.setattr(auth_api, "session_scope", fake_scope)
    monkeypatch.setattr(auth_api, "login", lambda *_args, **_kwargs: pair)
    client = configured_client(monkeypatch)
    payload = {
        "employee_number": "TEST-1001", "pin": "Z9Y8X7",
        "device_id": "device-fictional-user-0001", "device_label": "Intake Desk",
        "persistent": False,
    }
    response = client.post("/api/v1/auth/login", json=payload,
                           headers={"X-Client-Version": "1.0.0"})
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["profile"]["display_name"] == "Officer Avery Morgan"
    assert set(data) == set(asdict(pair))
    assert client.post("/api/v1/auth/login", json={**payload, "extra": "marker"},
                       headers={"X-Client-Version": "1.0.0"}).status_code == 400


def test_auth_route_fails_closed_without_audit_writer(monkeypatch):
    client = configured_client(monkeypatch)
    client.application.config.pop("AUDIT_WRITER")
    response = client.post("/api/v1/auth/renew", json={
        "renewal_token": "fictional-renewal-token",
        "device_id": "device-fictional-user-0001",
    }, headers={"X-Client-Version": "1.0.0"})
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "dependency_unavailable"


def test_login_route_rejects_invalid_device_before_service_call(monkeypatch):
    import backend.webapp.api_v1.auth as auth_api

    calls = []
    monkeypatch.setattr(auth_api, "login", lambda *_args, **_kwargs: calls.append(True))
    client = configured_client(monkeypatch)
    response = client.post("/api/v1/auth/login", json={
        "employee_number": "TEST-1001",
        "pin": "Z9Y8X7",
        "device_id": "short",
        "device_label": "Intake Desk",
        "persistent": False,
    }, headers={"X-Client-Version": "1.0.0"})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_failed"
    assert calls == []


def test_auth_routes_reject_malformed_secret_shapes_before_service_call(monkeypatch):
    import backend.webapp.api_v1.auth as auth_api

    calls = []
    monkeypatch.setattr(auth_api, "login", lambda *_args, **_kwargs: calls.append("login"))
    monkeypatch.setattr(auth_api, "renew_session", lambda *_args, **_kwargs: calls.append("renew"))
    client = configured_client(monkeypatch)
    login_response = client.post("/api/v1/auth/login", json={
        "employee_number": "TEST-1001", "pin": "!", "device_id": "device-fictional-user-0001",
        "device_label": "Desk", "persistent": False,
    }, headers={"X-Client-Version": "1.0.0"})
    renew_response = client.post("/api/v1/auth/renew", json={
        "renewal_token": "short", "device_id": "device-fictional-user-0001",
    }, headers={"X-Client-Version": "1.0.0"})
    assert login_response.status_code == renew_response.status_code == 400
    assert calls == []
