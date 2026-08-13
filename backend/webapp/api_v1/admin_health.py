"""Safe, elevated operational health data for the Access client.

This surface deliberately reports only stable status codes, bounded counts,
and deployment identifiers.  It never returns configuration, credentials,
query text, or report content.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime, timedelta

from flask import Blueprint, current_app, g
from sqlalchemy import func, select, union_all
from sqlalchemy.exc import SQLAlchemyError

from backend.build_info import build_metadata
from backend.identity.audit import AuditEventInput
from backend.persistence.database import DatabaseUnavailable, database_ready
from backend.persistence.models import AiJob, AuditEvent, Report, TaskOutbox
from backend.webapp.api_v1.context import request_id
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.middleware import (
    current_actor,
    current_request_session,
    require_access_token,
    require_admin_elevation,
    require_role,
)
from backend.webapp.api_v1.responses import success


admin_health_bp = Blueprint("admin_health_api", __name__)
logger = logging.getLogger("backend.webapp.operations")
_MAX_COUNT = 1_000_000_000
_SIGNAL_FIELDS = {
    "dependency_health": frozenset({"dependency", "latency_bucket"}),
    "queue_health": frozenset({"depth_bucket", "oldest_age_bucket", "job_type", "stage", "latency_bucket"}),
    "backup_restore_health": frozenset({"recency_bucket"}),
    "client_upgrade_required": frozenset({"parsed_client_version"}),
}
_STABLE_VALUE = re.compile(r"^[a-z0-9_]{1,64}$")
_FAILED_JOB_TYPES = ("classify", "extract", "generate", "disciplinary")
_QUEUE_AGE_BUCKETS = (
    "zero",
    "less_than_1m",
    "1m_to_5m",
    "5m_to_30m",
    "30m_to_2h",
    "2h_or_more",
)
_DURATION_BUCKETS = _QUEUE_AGE_BUCKETS[1:]
_STAGE_LATENCY_BUCKETS = (
    "less_than_1s",
    "1s_to_10s",
    "10s_to_60s",
    "1m_to_5m",
    "5m_or_more",
)


def _bounded_count(value: int) -> int:
    return min(max(int(value), 0), _MAX_COUNT)


def _emit(signal: str, result: str, **fields: str) -> None:
    """Emit the four RP-10 operational signal families without sensitive data."""
    allowed = _SIGNAL_FIELDS.get(signal)
    if allowed is None or set(fields) - allowed:
        raise ValueError("operational signal fields are invalid")
    if not _STABLE_VALUE.fullmatch(result) or any(
        not isinstance(value, str) or not _STABLE_VALUE.fullmatch(value) for value in fields.values()
    ):
        raise ValueError("operational signal values are invalid")
    logger.info(json.dumps({"signal": signal, "result": result, **fields}, sort_keys=True))


def emit_client_upgrade_required(parsed_client_version: str) -> None:
    """Emit the only allowed client-upgrade signal projection."""
    _emit(
        "client_upgrade_required",
        "required",
        parsed_client_version=parsed_client_version,
    )


def _age_bucket(duration: timedelta | None) -> str:
    """Project a non-negative duration into the closed health bucket enum."""
    if duration is None:
        return "unknown"
    seconds = max(duration.total_seconds(), 0)
    if seconds < 60:
        return _DURATION_BUCKETS[0]
    if seconds < 5 * 60:
        return _DURATION_BUCKETS[1]
    if seconds < 30 * 60:
        return _DURATION_BUCKETS[2]
    if seconds < 2 * 60 * 60:
        return _DURATION_BUCKETS[3]
    return _DURATION_BUCKETS[4]


def _latency_bucket(duration: timedelta | None) -> str:
    """Project failed-job stage duration into the closed second-scale enum."""
    if duration is None:
        return "unknown"
    seconds = max(duration.total_seconds(), 0)
    if seconds < 1:
        return _STAGE_LATENCY_BUCKETS[0]
    if seconds < 10:
        return _STAGE_LATENCY_BUCKETS[1]
    if seconds < 60:
        return _STAGE_LATENCY_BUCKETS[2]
    if seconds < 5 * 60:
        return _STAGE_LATENCY_BUCKETS[3]
    return _STAGE_LATENCY_BUCKETS[4]


def _policy_search_status() -> str:
    """Fail closed until policy search has an approved live safe producer."""
    return "Unavailable"


def _oldest_pending_or_running_at(session):
    """Return only the oldest pending outbox/running job time, never the value itself."""
    active_times = union_all(
        select(TaskOutbox.created_at.label("queued_at")).where(TaskOutbox.state == "pending"),
        select(func.coalesce(AiJob.started_at, AiJob.created_at).label("queued_at")).where(AiJob.state == "running"),
    ).subquery()
    return session.scalar(select(func.min(active_times.c.queued_at)))


def _failed_job_health(session) -> tuple[tuple[str, str], ...]:
    """Return one latest failed-job latency bucket per fixed job category."""
    signals = []
    for job_type in _FAILED_JOB_TYPES:
        row = session.execute(
            select(AiJob.started_at, AiJob.completed_at)
            .where(AiJob.state == "failed", AiJob.job_type == job_type)
            .order_by(AiJob.completed_at.desc(), AiJob.created_at.desc())
            .limit(1)
        ).one_or_none()
        if row is not None:
            started_at, completed_at = row
            duration = completed_at - started_at if started_at and completed_at else None
            signals.append((job_type, _latency_bucket(duration)))
    return tuple(signals)


def _emit_failed_job_health(jobs: tuple[tuple[str, str], ...]) -> None:
    """Emit one identifier-free failure signal for each bounded job category."""
    for job_type, latency_bucket in jobs:
        _emit(
            "queue_health",
            "failed",
            depth_bucket="unknown",
            oldest_age_bucket="unknown",
            job_type=job_type,
            stage="failed",
            latency_bucket=latency_bucket,
        )


def _component(name: str, status: str) -> dict[str, str]:
    return {"component": name, "status": status}


def _append_health_audit() -> None:
    actor = current_actor()
    current_app.config["AUDIT_WRITER"].append(
        current_request_session(),
        AuditEventInput(
            actor_account_id=actor.account_id,
            actor_staff_member_id=actor.staff_member_id,
            action="admin.health_viewed",
            result="success",
            request_id=request_id(),
            target_type="operations_health",
            target_id=None,
            details={},
            client_version=str(g.client_version),
        ),
    )


@admin_health_bp.get("/overview", endpoint="overview")
@require_access_token
@require_role("admin")
@require_admin_elevation
def overview():
    """Return compact, bounded operational counters for an elevated Admin."""
    db = current_request_session()
    try:
        return success(
            {
                "reports": _bounded_count(db.scalar(select(func.count()).select_from(Report)) or 0),
                "queued_jobs": _bounded_count(
                    db.scalar(select(func.count()).select_from(AiJob).where(AiJob.state == "queued")) or 0
                ),
                "pending_outbox": _bounded_count(
                    db.scalar(select(func.count()).select_from(TaskOutbox).where(TaskOutbox.state == "pending")) or 0
                ),
                "recent_audit_events": _bounded_count(db.scalar(select(func.count()).select_from(AuditEvent)) or 0),
                "build": build_metadata(),
            }
        )
    except (DatabaseUnavailable, SQLAlchemyError):
        g.identity_db_failed = True
        raise ApiError(
            "dependency_unavailable",
            "Operations data is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@admin_health_bp.get("/health", endpoint="health")
@require_access_token
@require_role("admin")
@require_admin_elevation
def health():
    """Return a deliberately small health snapshot and append an audit row."""
    db_status = "Operational" if database_ready() else "Unavailable"
    policy_search_status = _policy_search_status()
    backup_restore_status = "Unavailable"
    queue_status = "Operational"
    try:
        pending = (
            current_request_session().scalar(
                select(func.count()).select_from(TaskOutbox).where(TaskOutbox.state == "pending")
            )
            or 0
        )
        oldest_pending_or_running_at = _oldest_pending_or_running_at(current_request_session())
        failed_job_health = _failed_job_health(current_request_session())
        if pending > 10_000:
            queue_status = "Degraded"
        if failed_job_health:
            queue_status = "Degraded"
        _append_health_audit()
    except (DatabaseUnavailable, SQLAlchemyError):
        g.identity_db_failed = True
        raise ApiError(
            "dependency_unavailable",
            "Operations data is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    safe_database = db_status.lower()
    safe_queue = queue_status.lower()
    safe_policy_search = policy_search_status.lower()
    depth_bucket = "zero" if pending == 0 else "one_to_999" if pending < 1_000 else "1000_or_more"
    _emit(
        "dependency_health",
        safe_database,
        dependency="database",
        latency_bucket="unknown",
    )
    _emit(
        "dependency_health",
        safe_policy_search,
        dependency="policy_search",
        latency_bucket="unknown",
    )
    oldest_age_bucket = (
        "zero"
        if oldest_pending_or_running_at is None
        else _age_bucket(datetime.now(UTC) - oldest_pending_or_running_at)
    )
    _emit(
        "queue_health",
        safe_queue,
        depth_bucket=depth_bucket,
        oldest_age_bucket=oldest_age_bucket,
    )
    _emit_failed_job_health(failed_job_health)
    _emit("backup_restore_health", backup_restore_status.lower(), recency_bucket="unknown")
    overall = (
        "Unavailable"
        if "Unavailable" in {db_status, policy_search_status}
        else "Degraded"
        if (queue_status == "Degraded" or backup_restore_status == "Unavailable")
        else "Operational"
    )
    return success(
        {
            "status": overall,
            "components": [
                _component("database", db_status),
                _component("policy_search", policy_search_status),
                _component("queue", queue_status),
                _component("backup_restore", backup_restore_status),
            ],
            "build": build_metadata(),
        }
    )
