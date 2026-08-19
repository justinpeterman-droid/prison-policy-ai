"""Individual employee authentication for the Guided Operations browser client."""
from datetime import UTC, datetime
from hmac import compare_digest
import re

from flask import Blueprint, current_app, request
from sqlalchemy.exc import SQLAlchemyError

from backend.identity.accounts import InvalidCredentials
from backend.identity.browser_sessions import (
    BrowserCsrfInvalid,
    BrowserSessionInvalid,
    create_browser_session,
    renew_browser_session,
    resolve_browser_actor,
)
from backend.identity.config import IdentitySettings
from backend.identity.sessions import (
    SessionReauthenticationRequired,
    revoke_session,
)
from backend.identity.tokens import issue_credential
from backend.persistence.database import DatabaseUnavailable, session_scope
from backend.persistence.models import Account, StaffMember
from backend.persistence.models.browser import BrowserSessionBinding
from backend.webapp.api_v1.auth import _consume_login_limits
from backend.webapp.api_v1.context import request_id
from backend.webapp.api_v1.responses import failure, success
from backend.webapp.web_api.middleware import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    DEVICE_COOKIE,
    RENEWAL_COOKIE,
    current_browser_actor,
    current_browser_session,
    require_browser_csrf,
    require_browser_session,
    validate_same_origin_request,
)


auth_bp = Blueprint("web_auth", __name__)
_PIN = re.compile(r"^[A-Za-z0-9]{4,8}$")
_LOGIN_FIELDS = {"employee_number", "pin", "persistent"}

# The identity credentials stay scoped to the API paths that consume them, so a
# stray request to a legacy Jinja page never carries them. The CSRF value is the
# exception: it is the readable half of a double-submit pair, so the client at
# /workspace has to see it in document.cookie — and document.cookie only exposes
# cookies whose Path is a prefix of the *page's* path, not the fetch target's.
# Scoped to /api/web/v1 it is invisible to the SPA and every mutation 403s.
CREDENTIAL_COOKIE_PATH = "/api/web/v1"
RENEWAL_COOKIE_PATH = "/api/web/v1/auth"
CSRF_COOKIE_PATH = "/"


def _failure(code: str, message: str, status: int, *, retryable: bool = False):
    return failure(code, message, status, retryable=retryable)


def _json_exact(fields: set[str]) -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != fields:
        raise ValueError("The request body is invalid.")
    return payload


def _required_string(payload: dict, field: str, *, maximum: int = 120) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError("The request body is invalid.")
    return value


def _profile(db, actor) -> dict[str, object]:
    account = db.get(Account, actor.account_id)
    staff = db.get(StaffMember, actor.staff_member_id)
    if account is None or staff is None:
        raise BrowserSessionInvalid("Browser profile is unavailable.")
    return {
        "account_id": str(account.id),
        "staff_id": str(staff.id),
        "session_id": str(actor.session_id),
        "employee_number": staff.employee_number,
        "display_name": " ".join(
            value for value in (staff.rank, staff.first_name, staff.last_name) if value
        ),
        "rank": staff.rank,
        "shift": staff.shift,
        "role": account.role,
        "must_change_pin": account.must_change_pin,
    }


def _is_https() -> bool:
    forwarded = request.headers.get("X-Forwarded-Proto", "").split(",", 1)[0].strip()
    return request.is_secure or forwarded == "https"


def _max_age(expires_at: datetime) -> int:
    return max(1, int((expires_at - datetime.now(UTC)).total_seconds()))


def _write_session_cookies(response, cookies, device_id: str) -> None:
    secure = _is_https()
    renewal_age = _max_age(cookies.renewal_expires_at)
    response.set_cookie(
        ACCESS_COOKIE,
        cookies.access_token,
        max_age=_max_age(cookies.access_expires_at),
        httponly=True,
        secure=secure,
        samesite="Lax",
        path=CREDENTIAL_COOKIE_PATH,
    )
    response.set_cookie(
        RENEWAL_COOKIE,
        cookies.renewal_token,
        max_age=renewal_age if cookies.persistent else None,
        httponly=True,
        secure=secure,
        samesite="Lax",
        path=RENEWAL_COOKIE_PATH,
    )
    response.set_cookie(
        DEVICE_COOKIE,
        device_id,
        max_age=renewal_age if cookies.persistent else None,
        httponly=True,
        secure=secure,
        samesite="Lax",
        path=RENEWAL_COOKIE_PATH,
    )
    response.set_cookie(
        CSRF_COOKIE,
        cookies.csrf_token,
        max_age=renewal_age if cookies.persistent else None,
        httponly=False,
        secure=secure,
        samesite="Lax",
        path=CSRF_COOKIE_PATH,
    )


def _clear_session_cookies(response) -> None:
    for name, path, httponly in (
        (ACCESS_COOKIE, CREDENTIAL_COOKIE_PATH, True),
        (RENEWAL_COOKIE, RENEWAL_COOKIE_PATH, True),
        (DEVICE_COOKIE, RENEWAL_COOKIE_PATH, True),
        (CSRF_COOKIE, CSRF_COOKIE_PATH, False),
    ):
        response.delete_cookie(
            name,
            path=path,
            secure=_is_https(),
            httponly=httponly,
            samesite="Lax",
        )


def _device_label() -> str:
    value = (request.user_agent.string or "Web browser").strip()
    return value[:120] or "Web browser"


@auth_bp.post("/login", endpoint="login")
def login_route():
    try:
        validate_same_origin_request()
        payload = _json_exact(_LOGIN_FIELDS)
        employee_number = _required_string(payload, "employee_number", maximum=64)
        pin = _required_string(payload, "pin", maximum=8)
        if not _PIN.fullmatch(pin) or not isinstance(payload.get("persistent"), bool):
            raise ValueError("The request body is invalid.")
        settings: IdentitySettings = current_app.config["IDENTITY_SETTINGS"]
        audit_writer = current_app.config.get("AUDIT_WRITER")
        if audit_writer is None:
            raise DatabaseUnavailable("audit service unavailable")
        device_id = request.cookies.get(DEVICE_COOKIE, "") or issue_credential().raw
        with session_scope() as db:
            _consume_login_limits(
                db,
                {"employee_number": employee_number, "device_id": device_id},
                settings,
            )
            actor, cookies = create_browser_session(
                db,
                employee_number=employee_number,
                pin=pin,
                device_id=device_id,
                device_label=_device_label(),
                persistent=payload["persistent"],
                now=datetime.now(UTC),
                settings=settings,
                audit_writer=audit_writer,
                request_id=request_id(),
            )
            profile = _profile(db, actor)
        response = success({"authenticated": True, "profile": profile})
        _write_session_cookies(response, cookies, device_id)
        return response
    except BrowserCsrfInvalid:
        return _failure(
            "csrf_validation_failed",
            "The request could not be verified. Refresh the page and try again.",
            403,
        )
    except InvalidCredentials:
        return _failure("invalid_credentials", "The employee number or PIN is incorrect.", 401)
    except ValueError:
        return _failure("validation_failed", "The request body is invalid.", 400)
    except (BrowserSessionInvalid, DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        return _failure(
            "dependency_unavailable",
            "Authentication is temporarily unavailable.",
            503,
            retryable=True,
        )


@auth_bp.get("/session", endpoint="session")
def session_route():
    raw = request.cookies.get(ACCESS_COOKIE, "")
    if not raw:
        return success({"authenticated": False, "profile": None})
    try:
        with session_scope() as db:
            actor = resolve_browser_actor(db, access_token=raw, now=datetime.now(UTC))
            profile = _profile(db, actor)
        return success({"authenticated": True, "profile": profile})
    except SessionReauthenticationRequired:
        response = success({"authenticated": False, "profile": None})
        _clear_session_cookies(response)
        return response
    except (BrowserSessionInvalid, DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        return _failure(
            "dependency_unavailable",
            "Authentication is temporarily unavailable.",
            503,
            retryable=True,
        )


@auth_bp.post("/renew", endpoint="renew")
def renew_route():
    try:
        validate_same_origin_request()
        header = request.headers.get("X-CSRF-Token", "")
        cookie = request.cookies.get(CSRF_COOKIE, "")
        if not header or not cookie or not compare_digest(header, cookie):
            raise BrowserCsrfInvalid("CSRF confirmation is invalid.")
        renewal_token = request.cookies.get(RENEWAL_COOKIE, "")
        device_id = request.cookies.get(DEVICE_COOKIE, "")
        if not renewal_token or not device_id:
            raise SessionReauthenticationRequired("Sign in again.")
        settings: IdentitySettings = current_app.config["IDENTITY_SETTINGS"]
        audit_writer = current_app.config.get("AUDIT_WRITER")
        if audit_writer is None:
            raise DatabaseUnavailable("audit service unavailable")
        with session_scope() as db:
            actor, cookies = renew_browser_session(
                db,
                renewal_token=renewal_token,
                device_id=device_id,
                csrf_token=header,
                now=datetime.now(UTC),
                settings=settings,
                audit_writer=audit_writer,
                request_id=request_id(),
            )
            profile = _profile(db, actor)
        response = success({"authenticated": True, "profile": profile})
        _write_session_cookies(response, cookies, device_id)
        return response
    except BrowserCsrfInvalid:
        return _failure(
            "csrf_validation_failed",
            "The request could not be verified. Refresh the page and try again.",
            403,
        )
    except SessionReauthenticationRequired:
        response = _failure("authentication_required", "Sign in again.", 401)
        _clear_session_cookies(response)
        return response
    except (BrowserSessionInvalid, DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        return _failure(
            "dependency_unavailable",
            "Authentication is temporarily unavailable.",
            503,
            retryable=True,
        )


@auth_bp.post("/logout", endpoint="logout")
@require_browser_session
@require_browser_csrf
def logout_route():
    actor = current_browser_actor()
    db = current_browser_session()
    try:
        revoke_session(
            db,
            actor_account_id=actor.account_id,
            target_session_id=actor.session_id,
            now=datetime.now(UTC),
            audit_writer=current_app.config["AUDIT_WRITER"],
            request_id=request_id(),
        )
        binding = db.get(BrowserSessionBinding, actor.session_id)
        if binding is not None:
            db.delete(binding)
        response = success({"signed_out": True})
        _clear_session_cookies(response)
        return response
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db.rollback()
        return _failure(
            "dependency_unavailable",
            "Sign out could not be completed yet.",
            503,
            retryable=True,
        )
