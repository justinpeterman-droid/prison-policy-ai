"""Prison Policy AI — Flask web application with simple access-code auth."""
import os
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from flask import Flask, request, redirect, render_template, make_response, jsonify

from backend.pipeline.config import ACCESS_CODE, ADMIN_CODE, logger
from backend.webapp.assets import init_assets

TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

# Paths reachable without an access code
AUTH_EXEMPT = {"/login", "/logout", "/health"}

# Admin-only surface. The roster carries real staff names and employee numbers,
# so it is gated a tier above the rest of the site: the same login box takes
# either code, and only ADMIN_CODE opens these.
ADMIN_ONLY_EXACT = {"/roster", "/review-lab"}
ADMIN_ONLY_PREFIXES = ("/api/roster", "/api/review-lab")


def _matches(value: str, code: str) -> bool:
    """Case-insensitive comparison against a configured code."""
    return bool(code) and (value or "").strip().lower() == code.strip().lower()


def _code_ok(value: str) -> bool:
    """Whether a code opens the site at all. Either tier does."""
    return _matches(value, ACCESS_CODE) or _matches(value, ADMIN_CODE)


def _is_admin(value: str) -> bool:
    """Whether a code opens the admin tier (the roster)."""
    return _matches(value, ADMIN_CODE)


def _request_is_admin() -> bool:
    """Whether the current request carries the admin code.

    With no ACCESS_CODE the whole auth gate is off, so there is no meaningful
    tier to enforce and everyone is treated as admin — otherwise disabling auth
    for local work would silently take the roster away.
    """
    if not ACCESS_CODE:
        return True
    return _is_admin(request.cookies.get("access_code"))


def _is_admin_only(path: str) -> bool:
    return path in ADMIN_ONLY_EXACT or path.startswith(ADMIN_ONLY_PREFIXES)


# Pages a user can be sent to after logging in. `next` is attacker-controlled,
# so the redirect target is looked up in this table rather than derived from the
# request — nothing an attacker types can become part of the URL we emit.
NEXT_ALLOWED_PATHS = {"/", "/chat", "/reports", "/roster", "/review-lab"}


def _demo_targets() -> set[str]:
    """Every `/reports?demo=…` URL that actually means something.

    Built from the demo scenarios themselves, so an unknown id can't ride
    through login. Returning a member of this set — rather than reassembling
    the URL around the submitted value — is what keeps user input out of the
    Location header entirely.
    """
    targets = {"/reports?demo=1"}
    try:
        from backend.webapp.routes.reports import _load_demo_scenarios
        for scenario in _load_demo_scenarios():
            targets.add(f"/reports?demo={scenario['id']}")
            targets.add(f"/review-lab?demo={scenario['id']}")
    except Exception:  # pragma: no cover - demo data is optional
        logger.warning("Could not load demo scenarios for redirect allowlist")
    return targets


def _safe_next(value: str) -> str:
    """Resolve `next` to a known page on this site, or the home page.

    Every return value is a string this module produced, never the caller's.
    Absolute URLs, protocol-relative '//evil.com', backslash variants browsers
    normalize to slashes, unknown paths and unknown demo ids all collapse to '/'
    or drop back to the bare page.
    """
    parsed = urlsplit((value or "").strip())
    # A same-site reference has no scheme, host or credentials.
    if parsed.scheme or parsed.netloc:
        return "/"
    path = parsed.path
    if path not in NEXT_ALLOWED_PATHS:
        return "/"
    demo = parse_qs(parsed.query).get("demo", [""])[0]
    if path in {"/reports", "/review-lab"} and demo:
        candidate = f"{path}?demo={demo}"
        for known in _demo_targets():
            if known == candidate:
                return known
    # Look the path up rather than echoing it, so nothing user-supplied is
    # returned even when it happened to be valid.
    for known in NEXT_ALLOWED_PATHS:
        if known == path:
            return known
    return "/"


def _request_is_https() -> bool:
    """True when the client reached us over HTTPS. Cloud Run terminates TLS and
    forwards over HTTP, so trust X-Forwarded-Proto in addition to is_secure —
    otherwise the Secure cookie flag would never be set in production."""
    return request.is_secure or request.headers.get("X-Forwarded-Proto", "") == "https"


def _set_auth_cookie(resp, code: str):
    """Store the tier the submitted code unlocked, with hardening flags:
      - HttpOnly: JavaScript can't read it (XSS can't steal the session).
      - Secure:   only sent over HTTPS (in prod) — omitted on local http so dev login works.
      - SameSite=Lax: not sent on cross-site POST/XHR → blocks CSRF against the API.

    The cookie has to carry the tier, since that is what later requests check.
    But it stores the *configured* code rather than the string the user typed:
    matching is case-insensitive, so the two are equivalent, and this way no
    user-supplied text ever reaches the response — which is both what CodeQL
    wants and one less way for a stray value to end up in a Set-Cookie header.
    """
    resolved = ADMIN_CODE if _is_admin(code) else ACCESS_CODE
    resp.set_cookie(
        "access_code", resolved,
        max_age=60 * 60 * 24,
        httponly=True,
        secure=_request_is_https(),
        samesite="Lax",
    )
    return resp


def create_app() -> Flask:
    if ACCESS_CODE is None:
        raise RuntimeError(
            "ACCESS_CODE must be configured; set it to a non-empty secret in "
            "production or explicitly set ACCESS_CODE='' for isolated local work."
        )

    app = Flask(
        __name__,
        template_folder=str(TEMPLATE_DIR),
        static_folder=str(STATIC_DIR),
    )

    # Cap request bodies: field notes are text, so 1 MB is far more than any
    # real report. Prevents an oversized paste (or abuse) from running up
    # Vertex AI cost. Flask returns 413 automatically when exceeded.
    app.config["MAX_CONTENT_LENGTH"] = 1_000_000

    from backend.identity.config import IdentitySettings
    from backend.persistence.database import init_database

    identity_settings = IdentitySettings.from_env(os.environ)
    app.config["IDENTITY_SETTINGS"] = identity_settings
    init_database(identity_settings)

    # Content-versioned /static URLs, long-lived cache headers, and gzip for
    # text responses. Must be registered before the blueprints so its
    # after_request runs last (Flask runs them in reverse registration order).
    init_assets(app)

    # Routes
    from backend.webapp.routes.chat import chat_bp
    from backend.webapp.routes.reports import reports_bp
    from backend.webapp.routes.roster import roster_bp
    from backend.webapp.routes.feedback import feedback_bp
    from backend.webapp.routes.review_lab import review_lab_bp

    app.register_blueprint(chat_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(roster_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(review_lab_bp)
    if identity_settings.enabled:
        from backend.webapp.api_v1 import api_v1_bp

        app.register_blueprint(api_v1_bp)

    # Record the resolved search/model config at startup so the values actually
    # in use are visible in the logs — a config mismatch is the usual cause of a
    # chat outage, and there's no shell on Cloud Run to go inspect env vars.
    try:
        from backend.pipeline.query import log_search_config
        log_search_config()
    except Exception:  # pragma: no cover - never block startup over a log line
        logger.warning("Could not log search config", exc_info=True)

    @app.context_processor
    def inject_admin_flag():
        """`is_admin` in every template, so the nav can hide the roster link
        from users who couldn't open it anyway."""
        from backend.webapp.routes.review_lab import REVIEW_LAB_ENABLED
        return {
            "is_admin": _request_is_admin(),
            "review_lab_enabled": REVIEW_LAB_ENABLED,
        }

    @app.before_request
    def auth_gate():
        """Require the access code on every route except login/logout/health/static.

        Two tiers: ACCESS_CODE opens the site, ADMIN_CODE additionally opens the
        roster. A non-admin asking for an admin-only path gets a 404, not a 403 —
        the roster shouldn't advertise its own existence to someone who can't
        use it.
        """
        if request.path.startswith("/api/v1/"):
            return None
        if not ACCESS_CODE:
            return None
        if request.path in AUTH_EXEMPT or request.path.startswith("/static/"):
            return None
        if _code_ok(request.cookies.get("access_code")):
            if _is_admin_only(request.path) and not _request_is_admin():
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Not found."}), 404
                return render_template("404.html"), 404
            return None
        # Bookmarkable links: ?code=... sets the cookie then redirects clean
        submitted = request.args.get("code")
        if _code_ok(submitted):
            resp = make_response(redirect(request.path))
            return _set_auth_cookie(resp, submitted)
        if request.path.startswith("/api/"):
            return jsonify({"error": "Authentication required — reload the page to log in."}), 401
        # Preserve the query string, not just the path — otherwise a link like
        # /reports?demo=1 lands on a bare /reports after login. Normalized
        # through the same allowlist the login handler uses, so what we hand
        # back is built from constants either way.
        requested = request.full_path.rstrip("?") if request.query_string else request.path
        return redirect("/login?next=" + quote(_safe_next(requested), safe="/?=&"))

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
                target = _safe_next(request.args.get("next", "/"))
                # An admin link is the one case where the requested page needs
                # the tier the submitted code grants — send a non-admin home
                # rather than to a page that will 404 on them.
                if _is_admin_only(target) and not _is_admin(code):
                    target = "/"
                resp = make_response(redirect(target))
                return _set_auth_cookie(resp, code)
            error = "Invalid access code."
        return render_template("login.html", error=error,
                               next=_safe_next(request.args.get("next", "/")))

    @app.route("/logout")
    def logout():
        resp = make_response(redirect("/login"))
        resp.delete_cookie("access_code")
        return resp

    if ACCESS_CODE:
        logger.info("Access code auth enabled")
        if ADMIN_CODE:
            logger.info("Admin tier enabled — the Unit Roster requires ADMIN_CODE")
        else:
            logger.warning(
                "No ADMIN_CODE set — the Unit Roster is unreachable for everyone. "
                "Set ADMIN_CODE to give someone access to it.")
    else:
        logger.warning("No ACCESS_CODE set — app is open to the public")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080, debug=True)
