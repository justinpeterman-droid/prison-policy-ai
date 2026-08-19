"""Administrator elevation and step-up routes for Guided Operations."""
from datetime import UTC, datetime
import re

from flask import Blueprint, current_app, request
from sqlalchemy.exc import SQLAlchemyError

from backend.identity.browser_admin import (
    BrowserAdminStepUpRequired,
    browser_admin_state,
    enter_browser_admin_center,
    issue_browser_admin_step_up,
)
from backend.identity.elevation import STEP_UP_PURPOSES, StepUpRequired
from backend.persistence.database import DatabaseUnavailable
from backend.webapp.api_v1.context import request_id
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.responses import success
from backend.webapp.web_api.auth import _is_https
from backend.webapp.web_api.middleware import (
    current_browser_actor,
    current_browser_session,
    require_browser_csrf,
    require_browser_role,
    require_browser_session,
)


admin_auth_bp = Blueprint("web_admin_auth", __name__)
ADMIN_STEP_UP_COOKIE = "slut_web_admin_step_up"
ADMIN_STEP_UP_COOKIE_PATH = "/api/web/v1/admin"
_PIN = re.compile(r"^[A-Za-z0-9]{4,8}$")


def _timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _json_exact(fields: set[str]) -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != fields:
        raise ApiError(
            "validation_failed",
            "The administrator request is invalid.",
            status=400,
        )
    return payload


def _pin(payload: dict) -> str:
    value = payload.get("pin")
    if not isinstance(value, str) or not _PIN.fullmatch(value):
        raise ApiError(
            "validation_failed",
            "The administrator request is invalid.",
            status=400,
        )
    return value


def _audit_writer():
    writer = current_app.config.get("AUDIT_WRITER")
    if writer is None:
        raise ApiError(
            "dependency_unavailable",
            "Administrator security is temporarily unavailable.",
            status=503,
            retryable=True,
        )
    return writer


def _confirmation_error() -> ApiError:
    return ApiError(
        "admin_confirmation_required",
        "Administrator PIN confirmation is required.",
        status=401,
    )


@admin_auth_bp.get("/elevation", endpoint="elevation_state")
@require_browser_session
@require_browser_role("admin")
def elevation_state_route():
    try:
        state = browser_admin_state(
            current_browser_session(),
            actor=current_browser_actor(),
            now=datetime.now(UTC),
        )
        return success({
            "elevated": state.elevated,
            "elevation_expires_at": _timestamp(state.elevation_expires_at),
        })
    except PermissionError:
        raise ApiError("permission_denied", "Permission denied.", status=403) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Administrator security is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@admin_auth_bp.post("/elevation", endpoint="enter_elevation")
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def enter_elevation_route():
    payload = _json_exact({"pin"})
    try:
        state = enter_browser_admin_center(
            current_browser_session(),
            actor=current_browser_actor(),
            pin=_pin(payload),
            now=datetime.now(UTC),
            audit_writer=_audit_writer(),
            request_id=request_id(),
        )
        return success({
            "elevated": True,
            "elevation_expires_at": _timestamp(state.elevation_expires_at),
        })
    except (StepUpRequired, BrowserAdminStepUpRequired):
        raise _confirmation_error() from None
    except PermissionError:
        raise ApiError("permission_denied", "Permission denied.", status=403) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Administrator security is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@admin_auth_bp.post("/step-up", endpoint="step_up")
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def step_up_route():
    payload = _json_exact({"pin", "purpose"})
    purpose = payload.get("purpose")
    if not isinstance(purpose, str) or purpose not in STEP_UP_PURPOSES:
        raise ApiError(
            "validation_failed",
            "The administrator step-up purpose is invalid.",
            status=400,
        )
    try:
        issued = issue_browser_admin_step_up(
            current_browser_session(),
            actor=current_browser_actor(),
            pin=_pin(payload),
            purpose=purpose,
            now=datetime.now(UTC),
            audit_writer=_audit_writer(),
            request_id=request_id(),
        )
        response = success({
            "purpose": issued.purpose,
            "expires_at": _timestamp(issued.expires_at),
        })
        response.set_cookie(
            ADMIN_STEP_UP_COOKIE,
            issued.raw_token,
            max_age=300,
            httponly=True,
            secure=_is_https(),
            samesite="Lax",
            path=ADMIN_STEP_UP_COOKIE_PATH,
        )
        return response
    except (StepUpRequired, BrowserAdminStepUpRequired):
        raise _confirmation_error() from None
    except PermissionError:
        raise ApiError("permission_denied", "Permission denied.", status=403) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Administrator security is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
