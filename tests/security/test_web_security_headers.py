"""Browser-delivery security headers for the Guided Operations SPA."""

from flask import Flask

from backend.webapp.assets import init_assets
from backend.webapp.routes.web_app import web_app_bp


def _client(tmp_path):
    static = tmp_path / "static"
    web = static / "web"
    web.mkdir(parents=True)
    (web / "index.html").write_text("<!doctype html><title>Workspace</title>")
    (web / "app-3f7ae12c.js").write_text("console.log('workspace')")

    app = Flask(__name__, static_folder=str(static))
    init_assets(app)
    app.register_blueprint(web_app_bp)
    return app.test_client()


def test_workspace_document_has_strict_browser_security_headers(tmp_path):
    response = _client(tmp_path).get("/workspace")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Content-Security-Policy"] == (
        "default-src 'self'; base-uri 'self'; object-src 'none'; "
        "frame-ancestors 'none'; form-action 'self'; script-src 'self'; "
        "style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'"
    )
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Permissions-Policy"] == (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )


def test_vite_hashed_asset_is_immutable_but_spa_html_is_not(tmp_path):
    client = _client(tmp_path)

    asset = client.get("/static/web/app-3f7ae12c.js")
    document = client.get("/workspace")

    assert asset.headers["Cache-Control"] == "public, max-age=31536000, immutable"
    assert document.headers["Cache-Control"] == "no-store"
