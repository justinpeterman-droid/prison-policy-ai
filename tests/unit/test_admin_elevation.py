from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from flask import Flask, g
from sqlalchemy.exc import SQLAlchemyError

from backend.identity.elevation import (
    AdminElevationRequired,
    StepUpRequired,
    consume_step_up,
    elevation_is_active,
    touch_admin_elevation,
)
from backend.webapp.api_v1.middleware import require_admin_elevation, require_step_up


NOW = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
ACTOR = SimpleNamespace(account_id=uuid4(), staff_member_id=uuid4(), session_id=uuid4(), role="admin")


class Session:
    def __init__(self, scalar=None): self.value = scalar
    def scalar(self, _statement): return self.value
    def flush(self): return None


def test_elevation_is_idle_expiring_and_touch_slides_fifteen_minutes():
    row = SimpleNamespace(session_id=ACTOR.session_id, revoked_at=None,
                          idle_expires_at=NOW + timedelta(minutes=1), last_used_at=NOW)
    session = Session(row)
    assert elevation_is_active(session, ACTOR, NOW) is True
    touch_admin_elevation(session, ACTOR, NOW)
    assert row.idle_expires_at == NOW + timedelta(minutes=15)
    with pytest.raises(AdminElevationRequired):
        touch_admin_elevation(Session(None), ACTOR, NOW)


def test_step_up_is_single_use_and_bound_to_exact_session_and_purpose():
    token = "fictional-step-up-token"
    row = SimpleNamespace(session_id=ACTOR.session_id, purpose="account_reset_pin",
                          expires_at=NOW + timedelta(minutes=5), used_at=None, revoked_at=None)
    consume_step_up(Session(row), actor=ACTOR, raw_token=token,
                    purpose="account_reset_pin", now=NOW)
    assert row.used_at == NOW
    with pytest.raises(StepUpRequired):
        consume_step_up(Session(row), actor=ACTOR, raw_token=token,
                        purpose="account_reset_pin", now=NOW)


def test_missing_step_up_does_not_touch_or_extend_elevation(monkeypatch):
    import backend.webapp.api_v1.middleware as middleware

    calls = []
    monkeypatch.setattr(middleware, "touch_admin_elevation", lambda *_args: calls.append(True))
    app = Flask(__name__)

    @app.before_request
    def context():
        g.actor = ACTOR
        g.identity_db_session = object()

    @app.post("/mutation")
    @require_step_up("account_reset_pin")
    @require_admin_elevation
    def mutation():
        return {"ok": True}

    response = app.test_client().post("/mutation")
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "step_up_required"
    assert calls == []


def test_elevation_database_failure_is_safe_503(monkeypatch):
    import backend.webapp.api_v1.middleware as middleware

    monkeypatch.setattr(
        middleware, "touch_admin_elevation",
        lambda *_args: (_ for _ in ()).throw(SQLAlchemyError("database unavailable")),
    )
    app = Flask(__name__)

    @app.before_request
    def context():
        g.actor = ACTOR
        g.identity_db_session = object()

    @app.get("/admin")
    @require_admin_elevation
    def admin():
        return {"ok": True}

    response = app.test_client().get("/admin")
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "dependency_unavailable"
