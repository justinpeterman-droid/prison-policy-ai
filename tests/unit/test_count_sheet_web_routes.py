from flask import Flask

from backend.webapp.web_api.count_sheet import count_sheet_bp


def test_count_sheet_browser_routes_are_explicit():
    app = Flask(__name__)
    app.register_blueprint(count_sheet_bp, url_prefix="/api/web/v1")

    rules = {
        rule.rule: set(rule.methods or ())
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/api/web/v1/count-sheet")
    }

    assert "GET" in rules["/api/web/v1/count-sheet/definition"]
    assert {"GET", "POST"} <= rules["/api/web/v1/count-sheet"]
    assert "PATCH" in rules["/api/web/v1/count-sheet/<uuid:record_id>"]
