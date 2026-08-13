"""Safe, elevated operational health data for the Access client.

This surface deliberately reports only stable status codes, bounded counts,
and deployment identifiers.  It never returns configuration, credentials,
query text, or report content.
"""
from __future__ import annotations

import json
import logging
import re

from flask import Blueprint, current_app, g
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from backend.build_info import build_metadata
from backend.identity.audit import AuditEventInput
from backend.pipeline import config as pipeline_config
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
_MAX_FAILED_JOB_TYPES = 4


def _bounded_count(value: int) -> int:
    return min(max(int(value), 0), _MAX_COUNT)


def _emit(signal: str, result: str, **fields: str) -> None:
    """Emit the four RP-10 operational signal families without sensitive data."""
    allowed = _SIGNAL_FIELDS.get(signal)
    if allowed is None or set(fields) - allowed:
        raise ValueError("operational signal fields are invalid")
    if not _STABLE_VALUE.fullmatch(result) or any(
        not isinstance(value, str) or not _STABLE_VALUE.fullmatch(value)
        for value in fields.values()
    ):
        raise ValueError("operational signal values are invalid")
    logger.info(json.dumps({"signal": signal, "result": result, **fields}, sort_keys=True))


def emit_client_upgrade_required(parsed_client_version: str) -> None:
    """Emit the only allowed client-upgrade signal projection."""
    _emit("client_upgrade_required", "required", parsed_client_version=parsed_client_version)


def _policy_search_status() -> str:
    """Return a bounded readiness projection without exposing configuration."""
    required = (
        pipeline_config.PROJECT_ID,
        pipeline_config.AGENT_BUILDER_LOCATION,
        pipeline_config.AGENT_BUILDER_COLLECTION,
        pipeline_config.AGENT_BUILDER_ENGINE_ID,
        pipeline_config.AGENT_BUILDER_SERVING_CONFIG,
    )
    return "Operational" if all(isinstance(value, str) and value.strip() for value in required) else "Unavailable"


def _failed_job_types(session) -> tuple[str, ...]:
    """Return a small, deterministic projection of durable failed job types."""
    rows = session.scalars(
        select(AiJob.job_type)
        .where(AiJob.state == "failed")
        .distinct()
        .order_by(AiJob.job_type)
        .limit(_MAX_FAILED_JOB_TYPES)
    )
    return tuple(rows)


def _emit_failed_job_health(job_types: tuple[str, ...]) -> None:
    """Emit one identifier-free failure signal for each bounded job category."""
    for job_type in job_types:
        _emit(
            "queue_health", "failed",
            depth_bucket="unknown",
            oldest_age_bucket="unknown",
            job_type=job_type,
            stage="failed",
            latency_bucket="unknown",
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
        return success({
            "reports": _bounded_count(db.scalar(select(func.count()).select_from(Report)) or 0),
            "queued_jobs": _bounded_count(db.scalar(select(func.count()).select_from(AiJob).where(AiJob.state == "queued")) or 0),
            "pending_outbox": _bounded_count(db.scalar(select(func.count()).select_from(TaskOutbox).where(TaskOutbox.state == "pending")) or 0),
            "recent_audit_events": _bounded_count(db.scalar(select(func.count()).select_from(AuditEvent)) or 0),
            "build": build_metadata(),
        })
    except (DatabaseUnavailable, SQLAlchemyError):
        g.identity_db_failed = True
        raise ApiError("dependency_unavailable", "Operations data is temporarily unavailable.", status=503, retryable=True) from None


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
        pending = current_request_session().scalar(
            select(func.count()).select_from(TaskOutbox).where(TaskOutbox.state == "pending")
        ) or 0
        failed_job_types = _failed_job_types(current_request_session())
        if pending > 10_000:
            queue_status = "Degraded"
        if failed_job_types:
            queue_status = "Degraded"
        _append_health_audit()
    except (DatabaseUnavailable, SQLAlchemyError):
        g.identity_db_failed = True
        raise ApiError("dependency_unavailable", "Operations data is temporarily unavailable.", status=503, retryable=True) from None
    safe_database = db_status.lower()
    safe_queue = queue_status.lower()
    safe_policy_search = policy_search_status.lower()
    depth_bucket = "zero" if pending == 0 else "one_to_999" if pending < 1_000 else "1000_or_more"
    _emit("dependency_health", safe_database, dependency="database", latency_bucket="unknown")
    _emit("dependency_health", safe_policy_search, dependency="policy_search", latency_bucket="unknown")
    _emit("queue_health", safe_queue, depth_bucket=depth_bucket, oldest_age_bucket="unknown")
    _emit_failed_job_health(failed_job_types)
    _emit("backup_restore_health", backup_restore_status.lower(), recency_bucket="unknown")
    overall = "Unavailable" if "Unavailable" in {db_status, policy_search_status} else "Degraded" if (
        queue_status == "Degraded" or backup_restore_status == "Unavailable"
    ) else "Operational"
    return success({
        "status": overall,
        "components": [
            _component("database", db_status),
            _component("policy_search", policy_search_status),
            _component("queue", queue_status),
            _component("backup_restore", backup_restore_status),
        ],
        "build": build_metadata(),
    })
