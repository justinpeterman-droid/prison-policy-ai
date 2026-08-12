from uuid import uuid4

from flask import Flask, g

from backend.webapp.api_v1.middleware import Actor, require_pin_changed, require_role


def _client(actor, decorator):
    app = Flask(__name__)

    @app.before_request
    def assign_actor():
        g.actor = actor

    @app.get("/protected")
    @decorator
    def protected():
        return {"ok": True}

    return app.test_client()


def test_admin_role_is_declarative_and_denies_user():
    user = Actor(uuid4(), uuid4(), uuid4(), "user", 1, False)
    response = _client(user, require_role("admin")).get("/protected")
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "permission_denied"


def test_pin_change_guard_denies_only_must_change_actor():
    actor = Actor(uuid4(), uuid4(), uuid4(), "user", 1, True)
    response = _client(actor, require_pin_changed).get("/protected")
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "pin_change_required"
