from flask import Flask

from backend.webapp.web_api.forms_library import forms_library_bp


def _rules():
    app = Flask(__name__)
    app.register_blueprint(forms_library_bp, url_prefix="/api/web/v1")
    return {rule.rule: set(rule.methods or ()) for rule in app.url_map.iter_rules()}


def test_forms_library_browser_routes_match_the_approved_contract():
    rules = _rules()

    assert "GET" in rules["/api/web/v1/forms"]
    assert "GET" in rules["/api/web/v1/forms/<uuid:template_id>"]
    assert "POST" in rules["/api/web/v1/forms/selection/preview"]
    assert "POST" in rules["/api/web/v1/forms/selection/download"]
    assert not {"PATCH", "PUT", "DELETE"} & rules["/api/web/v1/forms"]
