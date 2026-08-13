from dataclasses import dataclass
from datetime import UTC, datetime
from functools import wraps
from typing import Literal
from uuid import UUID, uuid4

from flask import g, request
from sqlalchemy.exc import SQLAlchemyError

from backend.identity.sessions import SessionReauthenticationRequired, resolve_access_session
from backend.persistence.database import DatabaseUnavailable, session_scope
from backend.webapp.api_v1.responses import failure
from backend.webapp.api_v1.client_policy import MUST_CHANGE_PIN_ALLOWED_PATHS
from backend.identity.elevation import AdminElevationRequired, touch_admin_elevation


@dataclass(frozen=True)
class Actor:
    account_id: UUID
    staff_member_id: UUID
    session_id: UUID
    role: Literal["user", "admin"]
    auth_version: int
    must_change_pin: bool


def current_actor() -> Actor:
    actor = getattr(g, "actor", None)
    if actor is None:
        raise RuntimeError("authenticated actor is unavailable")
    return actor


def current_request_session():
    session = getattr(g, "identity_db_session", None)
    if session is None:
        raise RuntimeError("authenticated request session is unavailable")
    return session


def close_request_session(error=None) -> None:
    context = g.pop("identity_db_context", None)
    if context is None:
        return
    failed = error is not None or g.pop("identity_db_failed", False)
    g.pop("identity_db_session", None)
    if failed:
        try:
            marker = error or RuntimeError("request transaction failed")
            context.__exit__(type(marker), marker, marker.__traceback__)
        except BaseException:
            return
    else:
        context.__exit__(None, None, None)


def _failure(code: str, message: str, status: int, *, retryable: bool = False):
    if not hasattr(g, "request_id"):
        g.request_id = str(uuid4())
    g.api_error_code = code
    return failure(code, message, status, retryable=retryable)


def require_access_token(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        authorization = request.headers.get("Authorization", "")
        parts = authorization.split(" ")
        if len(parts) != 2 or parts[0] != "Bearer" or not parts[1]:
            return _failure("authentication_required", "Authentication is required.", 401)
        try:
            context = session_scope()
            db_session = context.__enter__()
            g.identity_db_context = context
            g.identity_db_session = db_session
            stored, account = resolve_access_session(
                db_session, access_token=parts[1], now=datetime.now(UTC)
            )
            g.actor = Actor(
                account.id, account.staff_member_id, stored.id, account.role,
                account.auth_version, account.must_change_pin,
            )
        except SessionReauthenticationRequired:
            g.identity_db_failed = True
            close_request_session()
            return _failure("authentication_required", "Authentication is required.", 401)
        except (DatabaseUnavailable, SQLAlchemyError):
            g.identity_db_failed = True
            close_request_session()
            return _failure(
                "dependency_unavailable", "Authentication is temporarily unavailable.",
                503, retryable=True,
            )
        if g.actor.must_change_pin and request.path not in MUST_CHANGE_PIN_ALLOWED_PATHS:
            return _failure(
                "pin_change_required", "Change the temporary PIN to continue.", 403
            )
        return view(*args, **kwargs)

    return wrapped


def require_role(role: str):
    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if current_actor().role != role:
                return _failure("permission_denied", "Permission denied.", 403)
            return view(*args, **kwargs)
        return wrapped
    return decorate


def require_pin_changed(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_actor().must_change_pin:
            return _failure("pin_change_required", "Change the temporary PIN to continue.", 403)
        return view(*args, **kwargs)
    return wrapped


def require_admin_elevation(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            touch_admin_elevation(
                current_request_session(), current_actor(), datetime.now(UTC)
            )
        except AdminElevationRequired:
            return _failure(
                "admin_elevation_required",
                "Administrator PIN confirmation is required.", 403,
            )
        except (DatabaseUnavailable, SQLAlchemyError):
            g.identity_db_failed = True
            return _failure(
                "dependency_unavailable", "The Admin service is temporarily unavailable.",
                503, retryable=True,
            )
        return view(*args, **kwargs)
    return wrapped


def require_step_up(purpose: str):
    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            raw = request.headers.get("X-Admin-Step-Up", "")
            if not raw:
                return _failure(
                    "step_up_required",
                    "Administrator PIN confirmation is required.", 403,
                )
            g.pending_step_up = (purpose, raw)
            return view(*args, **kwargs)
        return wrapped
    return decorate
