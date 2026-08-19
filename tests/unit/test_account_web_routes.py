from pathlib import Path

from flask import Flask

from backend.webapp.web_api.account import account_bp


def test_personal_account_routes_cover_pin_sessions_and_sign_out_everywhere():
    app = Flask(__name__)
    app.register_blueprint(account_bp, url_prefix="/api/web/v1/account")

    rules = {
        rule.rule: set(rule.methods or ())
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/api/web/v1/account")
    }

    assert "POST" in rules["/api/web/v1/account/change-pin"]
    assert "GET" in rules["/api/web/v1/account/sessions"]
    assert "DELETE" in rules["/api/web/v1/account/sessions/<uuid:session_id>"]
    assert "POST" in rules["/api/web/v1/account/logout-all"]


def test_account_adapter_uses_browser_guards_without_returning_credentials():
    source = Path("backend/webapp/web_api/account.py").read_text(encoding="utf-8")

    assert "require_browser_session" in source
    assert "require_browser_csrf" in source
    assert "current_browser_actor" in source
    assert "current_browser_session" in source
    assert "require_access_token" not in source

    # Changing a PIN rotates opaque HttpOnly cookies, so the adapter may handle
    # token values internally. It must never expose them as readable JSON keys.
    for key in ("access_token", "renewal_token", "csrf_token", "pin_hash"):
        assert f'"{key}"' not in source
        assert f"'{key}'" not in source
