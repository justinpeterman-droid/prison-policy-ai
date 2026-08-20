"""Serve the Guided Operations single-page application during pilot rollout."""
from pathlib import Path

from flask import Blueprint, current_app, make_response, send_from_directory


web_app_bp = Blueprint("web_app", __name__)

WORKSPACE_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; base-uri 'self'; object-src 'none'; "
        "frame-ancestors 'none'; form-action 'self'; script-src 'self'; "
        "style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}


def _web_root() -> Path:
    static_folder = current_app.static_folder
    if static_folder is None:
        raise RuntimeError("Flask static folder is unavailable")
    return Path(static_folder) / "web"


@web_app_bp.get("/workspace")
@web_app_bp.get("/workspace/<path:client_path>")
def workspace(client_path: str | None = None):
    """Return the SPA entry point for the preview route and client-side paths."""
    del client_path
    root = _web_root()
    if not (root / "index.html").is_file():
        return "Guided Operations preview has not been built.", 503
    response = make_response(send_from_directory(root, "index.html"))
    response.headers["Cache-Control"] = "no-store"
    response.headers.update(WORKSPACE_SECURITY_HEADERS)
    return response
