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

    assert any("change" in path and "pin" in path and "POST" in methods for path, methods in rules.items())
    assert any(path.endswith("/sessions") and "GET" in methods for path, methods in rules.items())
    assert any("<" in path and "session" in path and {"DELETE", "POST"} & methods for path, methods in rules.items())
    assert any("logout" in path and "all" in path and "POST" in methods for path, methods in rules.items())


def test_account_adapter_uses_browser_guards_without_returning_credentials():
    from pathlib import Path

    source = Path("backend/webapp/web_api/account.py").read_text(encoding="utf-8")

    assert "require_browser_session" in source
    assert "require_browser_csrf" in source
    assert "current_browser_actor" in source
    assert "current_browser_session" in source
    assert "require_access_token" not in source
    assert "access_token" not in source
    assert "renewal_token" not in source
