"""Prison Policy AI — Flask web application with simple access-code auth."""
from pathlib import Path
from flask import Flask, request, redirect, render_template, make_response, jsonify

from backend.pipeline.config import ACCESS_CODE, logger
from backend.webapp.assets import init_assets

TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

# Paths reachable without an access code
AUTH_EXEMPT = {"/login", "/logout", "/health"}


def _code_ok(value: str) -> bool:
    """Case-insensitive access-code check, so 'slut' and 'SLUT' both work."""
    return bool(ACCESS_CODE) and (value or "").strip().lower() == ACCESS_CODE.strip().lower()


def _request_is_https() -> bool:
    """True when the client reached us over HTTPS. Cloud Run terminates TLS and
    forwards over HTTP, so trust X-Forwarded-Proto in addition to is_secure —
    otherwise the Secure cookie flag would never be set in production."""
    return request.is_secure or request.headers.get("X-Forwarded-Proto", "") == "https"


def _set_auth_cookie(resp):
    """Set the access-code cookie with hardening flags:
      - HttpOnly: JavaScript can't read it (XSS can't steal the session).
      - Secure:   only sent over HTTPS (in prod) — omitted on local http so dev login works.
      - SameSite=Lax: not sent on cross-site POST/XHR → blocks CSRF against the API.
    """
    resp.set_cookie(
        "access_code", ACCESS_CODE,
        max_age=60 * 60 * 24,
        httponly=True,
        secure=_request_is_https(),
        samesite="Lax",
    )
    return resp


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(TEMPLATE_DIR),
        static_folder=str(STATIC_DIR),
    )

    # Cap request bodies: field notes are text, so 1 MB is far more than any
    # real report. Prevents an oversized paste (or abuse) from running up
    # Vertex AI cost. Flask returns 413 automatically when exceeded.
    app.config["MAX_CONTENT_LENGTH"] = 1_000_000

    # Content-versioned /static URLs, long-lived cache headers, and gzip for
    # text responses. Must be registered before the blueprints so its
    # after_request runs last (Flask runs them in reverse registration order).
    init_assets(app)

    # Routes
    from backend.webapp.routes.chat import chat_bp
    from backend.webapp.routes.reports import reports_bp
    from backend.webapp.routes.roster import roster_bp
    from backend.webapp.routes.feedback import feedback_bp

    app.register_blueprint(chat_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(roster_bp)
    app.register_blueprint(feedback_bp)

    # Record the resolved search/model config at startup so the values actually
    # in use are visible in the logs — a config mismatch is the usual cause of a
    # chat outage, and there's no shell on Cloud Run to go inspect env vars.
    try:
        from backend.pipeline.query import log_search_config
        log_search_config()
    except Exception:  # pragma: no cover - never block startup over a log line
        logger.warning("Could not log search config", exc_info=True)

    @app.before_request
    def auth_gate():
        """Require the access code on every route except login/logout/health/static."""
        if not ACCESS_CODE:
            return None
        if request.path in AUTH_EXEMPT or request.path.startswith("/static/"):
            return None
        if _code_ok(request.cookies.get("access_code")):
            return None
        # Bookmarkable links: ?code=... sets the cookie then redirects clean
        if _code_ok(request.args.get("code")):
            resp = make_response(redirect(request.path))
            return _set_auth_cookie(resp)
        if request.path.startswith("/api/"):
            return jsonify({"error": "Authentication required — reload the page to log in."}), 401
        return redirect(f"/login?next={request.path}")

    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/health")
    def health():
        return {"status": "ok"}

    @app.route("/roster")
    def roster_page():
        return render_template("roster.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            code = request.form.get("code", "")
            if _code_ok(code):
                next_url = request.args.get("next", "/")
                resp = make_response(redirect(next_url))
                return _set_auth_cookie(resp)
            error = "Invalid access code."
        return render_template("login.html", error=error, next=request.args.get("next", "/"))

    @app.route("/logout")
    def logout():
        resp = make_response(redirect("/login"))
        resp.delete_cookie("access_code")
        return resp

    if ACCESS_CODE:
        logger.info("Access code auth enabled")
    else:
        logger.warning("No ACCESS_CODE set — app is open to the public")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080, debug=True)
