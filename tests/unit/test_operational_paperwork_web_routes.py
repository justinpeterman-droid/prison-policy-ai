from flask import Flask

from backend.webapp.web_api.paperwork import paperwork_bp


def test_operational_paperwork_browser_routes_are_closed_and_versioned():
    app = Flask(__name__)
    app.register_blueprint(paperwork_bp, url_prefix="/api/web/v1")

    rules = {
        rule.rule: set(rule.methods or ())
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/api/web/v1/paperwork")
    }

    assert {"GET", "POST"} <= rules["/api/web/v1/paperwork"]
    assert {"GET", "PATCH"} <= rules[
        "/api/web/v1/paperwork/<uuid:record_id>"
    ]
    assert "GET" in rules[
        "/api/web/v1/paperwork/<uuid:record_id>/revisions"
    ]
    assert "POST" in rules[
        "/api/web/v1/paperwork/<uuid:record_id>/restore"
    ]
