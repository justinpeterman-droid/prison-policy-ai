import json
import importlib
import logging
from datetime import UTC, datetime
from uuid import uuid4

from backend.webapp import app as app_mod
from backend.webapp.api_v1.pagination import InvalidCursor, decode_cursor, encode_cursor
from backend.identity.sessions import SessionReauthenticationRequired


def configured_client(monkeypatch):
    monkeypatch.setattr(app_mod, "ACCESS_CODE", "legacy-user")
    monkeypatch.setenv("ACCESS_API_ENABLED", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://app:test@localhost/access_test")
    monkeypatch.setenv("IDENTITY_HASH_PEPPER", "p" * 32)
    monkeypatch.setenv("CURSOR_SIGNING_KEY", "c" * 32)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://review.example.gov")
    return app_mod.create_app().test_client()


def test_success_and_error_envelopes_have_exact_keys_and_headers(monkeypatch):
    client = configured_client(monkeypatch)
    success = client.get("/api/v1/client-policy", headers={"X-Request-ID": "request_1234"})
    assert success.status_code == 200
    assert set(success.get_json()) == {
        "data",
        "request_id",
        "server_time",
        "api_version",
    }
    assert success.headers["X-Request-ID"] == "request_1234"
    assert success.headers["Cache-Control"] == "no-store"

    failure = client.get("/api/v1/me", headers={"X-Client-Version": "1.0.0"})
    assert failure.status_code == 401
    assert set(failure.get_json()) == {
        "error",
        "request_id",
        "server_time",
        "api_version",
    }
    assert set(failure.get_json()["error"]) == {"code", "message", "retryable"}
    assert failure.headers["Cache-Control"] == "no-store"


def test_invalid_request_id_and_client_version_fail_safely(monkeypatch):
    client = configured_client(monkeypatch)
    invalid_id = "invalid marker with spaces"
    response = client.get(
        "/api/v1/me",
        headers={"X-Request-ID": invalid_id, "X-Client-Version": "not-a-version"},
    )
    body = response.get_json()
    assert response.status_code == 400
    assert body["error"]["code"] == "validation_failed"
    assert body["request_id"] != invalid_id
    assert str(uuid4()).count("-") == body["request_id"].count("-")


def test_unexpected_api_error_uses_safe_json_envelope(monkeypatch):
    api_v1 = importlib.import_module("backend.webapp.api_v1")
    marker = "fictional-internal-exception-marker"

    def fail_policy(_settings):
        raise RuntimeError(marker)

    monkeypatch.setattr(api_v1, "policy_data", fail_policy)
    client = configured_client(monkeypatch)
    response = client.get("/api/v1/client-policy")

    assert response.status_code == 500
    assert response.is_json
    body = response.get_json()
    assert set(body) == {"error", "request_id", "server_time", "api_version"}
    assert body["error"] == {
        "code": "internal_error",
        "message": "An unexpected error occurred.",
        "retryable": False,
    }
    assert marker not in response.get_data(as_text=True)
    assert response.headers["Cache-Control"] == "no-store"


def test_request_events_are_closed_and_exclude_sensitive_markers(monkeypatch, caplog):
    middleware = importlib.import_module("backend.webapp.api_v1.middleware")

    def reject_unknown_bearer(*_args, **_kwargs):
        raise SessionReauthenticationRequired

    monkeypatch.setattr(middleware, "resolve_access_session", reject_unknown_bearer)
    client = configured_client(monkeypatch)
    marker = "fictional-sensitive-marker"
    caplog.set_level(logging.INFO, logger="backend.webapp.api_v1")

    client.get(f"/api/v1/client-policy?query={marker}")
    client.get(
        f"/api/v1/me?path_marker={marker}",
        headers={
            "X-Client-Version": "1.0.0",
            "Authorization": f"Bearer {marker}",
            "X-Fictional-Identity": marker,
        },
    )

    events = [json.loads(record.message) for record in caplog.records if record.name == "backend.webapp.api_v1"]
    assert events
    for event in events:
        assert set(event) == {
            "request_id",
            "action",
            "result",
            "latency_ms",
            "latency_bucket",
            "http_status_class",
            "error_code",
            "client_version",
            "dependency",
        }
        assert marker not in json.dumps(event)
    assert any(event["result"] == "success" for event in events)
    assert any(event["error_code"] == "authentication_required" for event in events)


def test_signed_cursor_is_closed_and_tamper_evident():
    payload = {
        "created_at": datetime(2026, 8, 12, tzinfo=UTC).isoformat().replace("+00:00", "Z"),
        "id": str(uuid4()),
    }
    encoded = encode_cursor(payload, "c" * 32)
    assert decode_cursor(encoded, "c" * 32) == payload
    try:
        decode_cursor(encoded[:-1] + ("A" if encoded[-1] != "A" else "B"), "c" * 32)
    except InvalidCursor:
        pass
    else:
        raise AssertionError("altered cursor was accepted")
