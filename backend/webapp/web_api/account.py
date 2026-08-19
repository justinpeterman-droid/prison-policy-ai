"""Cookie-authenticated personal Account routes for Guided Operations."""
from datetime import UTC, datetime
import re
from uuid import UUID

from flask import Blueprint, current_app, request
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from backend.identity.accounts import InvalidCredentials
from backend.identity.browser_sessions import BrowserCookiePair
from backend.identity.config import IdentitySettings
from backend.identity.sessions import (
    SessionReauthenticationRequired,
    change_pin,
    list_sessions,
    logout_all,
    revoke_session,
)
from backend.persistence.database import DatabaseUnavailable
from backend.persistence.models.browser import BrowserSessionBinding
from backend.persistence.models.sessions import AccessSession
from backend.webapp.api_v1.context import request_id
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.responses import success
from backend.webapp.web_api.auth import _clear_session_cookies, _write_session_cookies
from backend.webapp.web_api.middleware import (
    CSRF_COOKIE,
    DEVICE_COOKIE,
    current_browser_actor,
    current_browser_session,
    require_browser_csrf,
    require_browser_session,
)


account_bp = Blueprint("web_account", __name__)
_PIN = re.compile(r"^[A-Za-z0-9]{4,8}$")


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _json_exact(fields: set[str]) -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != fields:
        raise ApiError("validation_failed", "The account request is invalid.", status=400)
    return payload


def _pin(payload: dict, field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not _PIN.fullmatch(value):
        raise ApiError("validation_failed", "The account request is invalid.", status=400)
    return value


def _audit_writer():
    writer = current_app.config.get("AUDIT_WRITER")
    if writer is None:
        raise ApiError(
            "dependency_unavailable",
            "Account security is temporarily unavailable.",
            status=503,
            retryable=True,
        )
    return writer


@account_bp.post("/change-pin", endpoint="change_pin")
@require_browser_session
@require_browser_csrf
def change_pin_route():
    payload = _json_exact({"current_pin", "new_pin"})
    current_pin = _pin(payload, "current_pin")
    new_pin = _pin(payload, "new_pin")
    if current_pin == new_pin:
        raise ApiError("validation_failed", "Choose a different new PIN.", status=400)

    actor = current_browser_actor()
    db = current_browser_session()
    settings: IdentitySettings = current_app.config["IDENTITY_SETTINGS"]
    device_id = request.cookies.get(DEVICE_COOKIE, "")
    csrf_token = request.cookies.get(CSRF_COOKIE, "")
    if not device_id or not csrf_token:
        raise ApiError("authentication_required", "Sign in again to change the PIN.", status=401)

    try:
        pair = change_pin(
            db,
            account_id=actor.account_id,
            current_session_id=actor.session_id,
            current_pin=current_pin,
            new_pin=new_pin,
            device_id=device_id,
            now=datetime.now(UTC),
            settings=settings,
            audit_writer=_audit_writer(),
            request_id=request_id(),
        )
        cookies = BrowserCookiePair(
            access_token=pair.access_token,
            renewal_token=pair.renewal_token,
            csrf_token=csrf_token,
            access_expires_at=pair.access_expires_at,
            renewal_expires_at=pair.renewal_expires_at,
            persistent=pair.persistent,
        )
        response = success({
            "changed": True,
            "session_id": str(pair.session_id),
            "must_change_pin": pair.requires_pin_change,
        })
        _write_session_cookies(response, cookies, device_id)
        return response
    except InvalidCredentials:
        raise ApiError("invalid_credentials", "The current PIN is incorrect.", status=401) from None
    except ValueError as error:
        raise ApiError("validation_failed", str(error), status=400) from None
    except SessionReauthenticationRequired:
        raise ApiError("authentication_required", "Sign in again to change the PIN.", status=401) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "The PIN could not be changed yet.",
            status=503,
            retryable=True,
        ) from None


@account_bp.get("/sessions", endpoint="sessions")
@require_browser_session
def sessions_route():
    actor = current_browser_actor()
    db = current_browser_session()
    try:
        rows = list_sessions(
            db,
            account_id=actor.account_id,
            current_session_id=actor.session_id,
        )
        return success({
            "items": [
                {
                    "session_id": str(row.session_id),
                    "device_label": row.device_label,
                    "persistent": row.persistent,
                    "created_at": _timestamp(row.created_at),
                    "last_seen_at": _timestamp(row.last_used_at),
                    "expires_at": _timestamp(row.renewal_expires_at),
                    "current": row.current,
                }
                for row in rows
            ]
        })
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Active sessions are temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@account_bp.delete("/sessions/<uuid:session_id>", endpoint="delete_session")
@require_browser_session
@require_browser_csrf
def delete_session_route(session_id: UUID):
    actor = current_browser_actor()
    db = current_browser_session()
    try:
        revoke_session(
            db,
            actor_account_id=actor.account_id,
            target_session_id=session_id,
            now=datetime.now(UTC),
            audit_writer=_audit_writer(),
            request_id=request_id(),
        )
        binding = db.get(BrowserSessionBinding, session_id)
        if binding is not None:
            db.delete(binding)
        response = success({"session_id": str(session_id), "revoked": True})
        if session_id == actor.session_id:
            _clear_session_cookies(response)
        return response
    except SessionReauthenticationRequired:
        raise ApiError("not_found", "The browser session was not found.", status=404) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "The browser session could not be signed out yet.",
            status=503,
            retryable=True,
        ) from None


@account_bp.post("/logout-all", endpoint="logout_all")
@require_browser_session
@require_browser_csrf
def logout_all_route():
    actor = current_browser_actor()
    db = current_browser_session()
    try:
        count = logout_all(
            db,
            account_id=actor.account_id,
            now=datetime.now(UTC),
            audit_writer=_audit_writer(),
            request_id=request_id(),
        )
        session_ids = select(AccessSession.id).where(
            AccessSession.account_id == actor.account_id
        )
        db.execute(delete(BrowserSessionBinding).where(
            BrowserSessionBinding.session_id.in_(session_ids)
        ))
        response = success({"signed_out": True, "session_count": count})
        _clear_session_cookies(response)
        return response
    except SessionReauthenticationRequired:
        raise ApiError("authentication_required", "Sign in again.", status=401) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Sessions could not be signed out yet.",
            status=503,
            retryable=True,
        ) from None
