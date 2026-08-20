"""Secure browser handoff from Guided Operations Admin to Review Lab."""
from datetime import UTC, datetime

from flask import Blueprint, current_app, request
from sqlalchemy.exc import SQLAlchemyError

from backend.identity.browser_admin import require_browser_admin_elevation
from backend.identity.browser_handoffs import HandoffInvalid, issue_browser_handoff
from backend.identity.elevation import AdminElevationRequired, StepUpRequired
from backend.persistence.database import DatabaseUnavailable
from backend.webapp.api_v1.context import request_id
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.responses import success
from backend.webapp.web_api.admin_auth import (
    ADMIN_STEP_UP_COOKIE,
    ADMIN_STEP_UP_COOKIE_PATH,
)
from backend.webapp.web_api.auth import _is_https
from backend.webapp.web_api.middleware import (
    current_browser_actor,
    current_browser_session,
    require_browser_csrf,
    require_browser_role,
    require_browser_session,
)


admin_review_lab_bp = Blueprint("web_admin_review_lab", __name__)


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _require_elevation() -> None:
    try:
        require_browser_admin_elevation(
            current_browser_session(),
            actor=current_browser_actor(),
            now=datetime.now(UTC),
        )
    except AdminElevationRequired:
        raise ApiError(
            "admin_elevation_required",
            "Administrator PIN confirmation is required.",
            status=403,
        ) from None


def _clear_step_up(response):
    response.delete_cookie(
        ADMIN_STEP_UP_COOKIE,
        path=ADMIN_STEP_UP_COOKIE_PATH,
        secure=_is_https(),
        httponly=True,
        samesite="Lax",
    )
    return response


@admin_review_lab_bp.post("/review-lab-handoffs", endpoint="issue_handoff")
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def issue_handoff_route():
    if request.data:
        raise ApiError(
            "validation_failed",
            "This operation does not accept a request body.",
            status=400,
        )
    _require_elevation()
    raw_step_up = request.cookies.get(ADMIN_STEP_UP_COOKIE, "")
    if not raw_step_up:
        raise ApiError(
            "step_up_required",
            "Administrator PIN confirmation is required.",
            status=403,
        )

    db = current_browser_session()
    try:
        result = issue_browser_handoff(
            db,
            actor=current_browser_actor(),
            now=datetime.now(UTC),
            audit_writer=current_app.config["AUDIT_WRITER"],
            request_id=request_id(),
            step_up_token=raw_step_up,
        )
        db.commit()
        response = success({
            "url": f"/access-handoff#{result.token}",
            "expires_at": _timestamp(result.expires_at),
        })
        return _clear_step_up(response)
    except (StepUpRequired, AdminElevationRequired):
        db.rollback()
        raise ApiError(
            "step_up_required",
            "Administrator PIN confirmation is required.",
            status=403,
        ) from None
    except HandoffInvalid:
        db.rollback()
        raise ApiError("permission_denied", "Permission denied.", status=403) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db.rollback()
        raise ApiError(
            "dependency_unavailable",
            "Review Lab access is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
