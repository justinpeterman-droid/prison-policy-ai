"""Authentication and CSRF guards for the cookie-authenticated web API."""
from datetime import UTC, datetime
from functools import wraps
from hmac import compare_digest
from urllib.parse import urlsplit

from flask import g, request
from sqlalchemy.exc import SQLAlchemyError

from backend.identity.browser_sessions import (
    BrowserActor,
    BrowserCsrfInvalid,
    resolve_browser_actor,
    validate_browser_csrf,
)
from backend.identity.sessions import SessionReauthenticationRequired
from backend.persistence.database import DatabaseUnavailable, session_scope
from backend.webapp.api_v1.responses import failure


ACCESS_COOKIE = "slut_web_access"
RENEWAL_COOKIE = "slut_web_renewal"
DEVICE_COOKIE = "slut_web_device"
CSRF_COOKIE = "slut_web_csrf"


def current_browser_actor() -> BrowserActor:
    actor = getattr(g, "browser_actor", None)
    if actor is None:
        raise RuntimeError("browser actor is unavailable")
    return actor


def current_browser_session():
    db = getattr(g, "browser_db_session", None)
    if db is None:
        raise RuntimeError("browser request session is unavailable")
    return db


def close_browser_request(error=None) -> None:
    context = g.pop("browser_db_context", None)
    if context is None:
        return
    db = g.pop("browser_db_session", None)
    failed = error is not None or g.pop("browser_db_failed", False)
    if failed and db is not None:
        db.rollback()
    context.__exit__(type(error), error, getattr(error, "__traceback__", None)) if error else context.__exit__(None, None, None)


def _failure(code: str, message: str, status: int, *, retryable: bool = False):
    g.api_error_code = code
    return failure(code, message, status, retryable=retryable)


def require_browser_session(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        raw = request.cookies.get(ACCESS_COOKIE, "")
        if not raw:
            return _failure("authentication_required", "Authentication is required.", 401)
        try:
            context = session_scope()
            db = context.__enter__()
            g.browser_db_context = context
            g.browser_db_session = db
            g.browser_actor = resolve_browser_actor(db, access_token=raw, now=datetime.now(UTC))
        except SessionReauthenticationRequired:
            g.browser_db_failed = True
            close_browser_request()
            return _failure("authentication_required", "Authentication is required.", 401)
        except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
            g.browser_db_failed = True
            close_browser_request()
            return _failure(
                "dependency_unavailable",
                "Authentication is temporarily unavailable.",
                503,
                retryable=True,
            )
        return view(*args, **kwargs)

    return wrapped


def validate_same_origin_request() -> None:
    """Reject cross-site writes before any credential or content is processed."""
    fetch_site = request.headers.get("Sec-Fetch-Site", "")
    if fetch_site and fetch_site not in {"same-origin", "none"}:
        raise BrowserCsrfInvalid("Same-origin confirmation is required.")

    origin = request.headers.get("Origin", "")
    if not origin:
        raise BrowserCsrfInvalid("Request origin is required.")
    parsed = urlsplit(origin)
    request_scheme = (
        request.headers.get("X-Forwarded-Proto", "").split(",", 1)[0].strip()
        or request.scheme
    )
    expected = f"{request_scheme}://{request.host}"
    supplied = f"{parsed.scheme}://{parsed.netloc}"
    if not compare_digest(supplied, expected):
        raise BrowserCsrfInvalid("Request origin is invalid.")


def require_browser_csrf(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            validate_same_origin_request()
            header = request.headers.get("X-CSRF-Token", "")
            cookie = request.cookies.get(CSRF_COOKIE, "")
            if not header or not cookie or not compare_digest(header, cookie):
                raise BrowserCsrfInvalid("CSRF confirmation is invalid.")
            validate_browser_csrf(
                current_browser_session(),
                actor=current_browser_actor(),
                supplied_token=header,
            )
        except BrowserCsrfInvalid:
            return _failure(
                "csrf_validation_failed",
                "The request could not be verified. Refresh the page and try again.",
                403,
            )
        return view(*args, **kwargs)

    return wrapped


def require_browser_role(role: str):
    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if current_browser_actor().role != role:
                return _failure("permission_denied", "Permission denied.", 403)
            return view(*args, **kwargs)

        return wrapped

    return decorate
