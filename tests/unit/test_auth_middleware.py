from types import SimpleNamespace
from uuid import uuid4

import pytest
from flask import Flask, g

from backend.webapp.api_v1.middleware import (
    Actor,
    close_request_session,
    current_actor,
    require_access_token,
)


def test_actor_is_frozen_and_contains_only_authoritative_ids():
    actor = Actor(uuid4(), uuid4(), uuid4(), "user", 3, False)
    with pytest.raises(Exception):
        actor.role = "admin"
    assert set(actor.__dict__) == {
        "account_id",
        "staff_member_id",
        "session_id",
        "role",
        "auth_version",
        "must_change_pin",
    }


def test_missing_or_malformed_bearer_is_authentication_required():
    app = Flask(__name__)

    @app.get("/protected")
    @require_access_token
    def protected():
        return {"actor": str(current_actor().account_id)}

    client = app.test_client()
    for header in (None, "Basic marker", "Bearer", "Bearer one two"):
        headers = {} if header is None else {"Authorization": header}
        response = client.get("/protected", headers=headers)
        assert response.status_code == 401
        assert response.get_json()["error"]["code"] == "authentication_required"


def test_bearer_resolution_stores_actor_not_raw_token(monkeypatch):
    import backend.webapp.api_v1.middleware as middleware

    account_id, staff_id, session_id = uuid4(), uuid4(), uuid4()
    stored = SimpleNamespace(id=session_id, auth_version=2)
    account = SimpleNamespace(
        id=account_id,
        staff_member_id=staff_id,
        role="admin",
        auth_version=2,
        must_change_pin=False,
    )

    scope_state = {"entered": False, "exited": False}

    class Scope:
        def __enter__(self):
            scope_state["entered"] = True
            return object()

        def __exit__(self, *_args):
            scope_state["exited"] = True
            return False

    monkeypatch.setattr(middleware, "session_scope", lambda: Scope())
    monkeypatch.setattr(
        middleware,
        "resolve_access_session",
        lambda *_args, **_kwargs: (stored, account),
    )
    app = Flask(__name__)
    app.teardown_request(close_request_session)

    @app.get("/protected")
    @require_access_token
    def protected():
        return {
            "role": current_actor().role,
            "g_keys": sorted(g.__dict__),
            "session_open_during_view": scope_state["entered"]
            and not scope_state["exited"],
        }

    response = app.test_client().get(
        "/protected", headers={"Authorization": "Bearer fictional-token"}
    )
    assert response.status_code == 200
    assert response.get_json()["role"] == "admin"
    assert response.get_json()["session_open_during_view"] is True
    assert scope_state["exited"] is True
    assert "fictional-token" not in response.get_data(as_text=True)
    assert "bearer" not in response.get_json()["g_keys"]


def test_protected_mutation_maps_domain_failure_without_500(monkeypatch):
    import backend.webapp.api_v1.auth as auth_api
    import backend.webapp.api_v1.middleware as middleware
    from backend.identity.errors import InvalidCredentials
    from backend.webapp import app as app_mod

    account_id, staff_id, session_id = uuid4(), uuid4(), uuid4()
    stored = SimpleNamespace(id=session_id)
    account = SimpleNamespace(
        id=account_id,
        staff_member_id=staff_id,
        role="user",
        auth_version=1,
        must_change_pin=False,
    )

    class Db:
        def __init__(self):
            self.rolled_back = False

        def rollback(self):
            self.rolled_back = True

    db = Db()

    class Scope:
        def __enter__(self):
            return db

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(app_mod, "ACCESS_CODE", "legacy-user")
    monkeypatch.setenv("ACCESS_API_ENABLED", "true")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://app:test@localhost/access_test"
    )
    monkeypatch.setenv("IDENTITY_HASH_PEPPER", "p" * 32)
    monkeypatch.setenv("CURSOR_SIGNING_KEY", "c" * 32)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://review.example.gov")
    monkeypatch.setattr(middleware, "session_scope", lambda: Scope())
    monkeypatch.setattr(
        middleware,
        "resolve_access_session",
        lambda *_args, **_kwargs: (stored, account),
    )
    monkeypatch.setattr(
        auth_api,
        "change_pin",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(InvalidCredentials("invalid")),
    )
    monkeypatch.setattr(
        auth_api,
        "claim_idempotency",
        lambda *_args, **_kwargs: SimpleNamespace(replayed=False),
    )
    client = app_mod.create_app().test_client()
    response = client.post(
        "/api/v1/auth/change-pin",
        json={"current_pin": "Z9Y8X7", "new_pin": "Q7W9E2"},
        headers={
            "Authorization": "Bearer fictional-token",
            "X-Client-Version": "1.0.0",
            "X-Device-ID": "device-fictional-user-0001",
            "Idempotency-Key": "change-pin-test-0001",
        },
    )
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "invalid_credentials"
    assert db.rolled_back is True

    from backend.identity.errors import PinPolicyError

    monkeypatch.setattr(
        auth_api,
        "change_pin",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(PinPolicyError("obvious PIN")),
    )
    policy_response = client.post(
        "/api/v1/auth/change-pin",
        json={"current_pin": "Z9Y8X7", "new_pin": "1234"},
        headers={
            "Authorization": "Bearer fictional-token",
            "X-Client-Version": "1.0.0",
            "X-Device-ID": "device-fictional-user-0001",
            "Idempotency-Key": "change-pin-test-0002",
        },
    )
    assert policy_response.status_code == 400
    assert policy_response.get_json()["error"]["code"] == "validation_failed"
