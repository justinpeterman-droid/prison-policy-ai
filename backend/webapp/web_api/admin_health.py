"""Safe, read-only administrator system health route."""
from datetime import UTC, datetime

from flask import Blueprint
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from backend.build_info import build_metadata
from backend.identity.browser_admin import require_browser_admin_elevation
from backend.identity.elevation import AdminElevationRequired
from backend.persistence.database import DatabaseUnavailable
from backend.persistence.models.jobs import AiJob, TaskOutbox
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.responses import success
from backend.webapp.web_api.middleware import (
    current_browser_actor,
    current_browser_session,
    require_browser_role,
    require_browser_session,
)


admin_health_bp = Blueprint("web_admin_health", __name__)
_ALLOWED = {"Operational", "Degraded", "Unavailable"}


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


def _checked_at() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _bounded_status(value: str) -> str:
    if value not in _ALLOWED:
        return "Unavailable"
    return value


def _health_snapshot() -> dict[str, object]:
    db = current_browser_session()
    try:
        pending_outbox = db.scalar(
            select(func.count()).select_from(TaskOutbox).where(
                TaskOutbox.state == "pending"
            )
        ) or 0
        failed_outbox = db.scalar(
            select(func.count()).select_from(TaskOutbox).where(
                TaskOutbox.state == "failed"
            )
        ) or 0
        failed_jobs = db.scalar(
            select(func.count()).select_from(AiJob).where(AiJob.state == "failed")
        ) or 0
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "System health is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None

    queue_status = (
        "Unavailable" if failed_outbox > 1000
        else "Degraded" if failed_outbox > 0 or pending_outbox > 10_000
        else "Operational"
    )
    ai_status = "Degraded" if failed_jobs > 0 else "Operational"
    components = {
        "api": "Operational",
        "database": "Operational",
        "ai": ai_status,
        "policy_expert": ai_status,
        "queue": queue_status,
        # No browser-accessible backup verifier exists today. Reporting a
        # stable unavailable state is safer than inventing green status.
        "backups": "Unavailable",
    }
    components = {key: _bounded_status(value) for key, value in components.items()}
    notices: list[dict[str, str]] = []
    if ai_status != "Operational":
        notices.append({
            "component": "ai",
            "status": ai_status,
            "message": "Recent AI work includes failed jobs.",
        })
    if queue_status != "Operational":
        notices.append({
            "component": "queue",
            "status": queue_status,
            "message": "Background work needs attention.",
        })
    notices.append({
        "component": "backups",
        "status": "Unavailable",
        "message": "Backup restore verification is not exposed in this workspace.",
    })
    return {
        "checked_at": _checked_at(),
        "components": components,
        "build": build_metadata(),
        "notices": notices[:10],
    }


@admin_health_bp.get("/health", endpoint="health")
@require_browser_session
@require_browser_role("admin")
def health_route():
    _require_elevation()
    return success(_health_snapshot())
