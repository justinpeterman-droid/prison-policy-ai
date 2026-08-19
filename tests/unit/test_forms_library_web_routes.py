from flask import Flask

from backend.webapp.web_api.forms_library import forms_library_bp


def test_forms_library_browser_route_is_read_only():
    app = Flask(__name__)
    app.register_blueprint(forms_library_bp, url_prefix="/api/web/v1")

    rule = next(
        rule
        for rule in app.url_map.iter_rules()
        if rule.rule == "/api/web/v1/forms-library"
    )
    assert "GET" in rule.methods
    assert not {"POST", "PATCH", "PUT", "DELETE"} & set(rule.methods or ())
