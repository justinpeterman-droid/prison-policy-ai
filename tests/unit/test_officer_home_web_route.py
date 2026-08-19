from flask import Flask

from backend.webapp.web_api.home import home_bp


def test_officer_home_summary_route_is_read_only():
    app = Flask(__name__)
    app.register_blueprint(home_bp, url_prefix="/api/web/v1")

    rule = next(
        rule
        for rule in app.url_map.iter_rules()
        if rule.rule == "/api/web/v1/home"
    )
    assert "GET" in rule.methods
    assert not {"POST", "PATCH", "PUT", "DELETE"} & set(rule.methods or ())
