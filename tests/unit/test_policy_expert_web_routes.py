from flask import Flask

from backend.webapp.web_api.policy import policy_bp


def test_policy_expert_browser_route_is_registered_as_a_write():
    app = Flask(__name__)
    app.register_blueprint(policy_bp, url_prefix="/api/web/v1/policy")

    rules = [
        rule
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/api/web/v1/policy")
    ]
    assert len(rules) == 1
    assert "POST" in set(rules[0].methods or ())


def test_policy_adapter_uses_browser_guards_not_bearer_tokens():
    source = __import__(
        "pathlib"
    ).Path("backend/webapp/web_api/policy.py").read_text(encoding="utf-8")

    assert "require_browser_session" in source
    assert "require_browser_csrf" in source
    assert "current_browser_actor" in source
    assert "current_browser_session" in source
    assert "require_access_token" not in source
