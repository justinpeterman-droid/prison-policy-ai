"""Read-only, privacy-preserving administrator audit routes."""
from datetime import UTC, datetime
import re
from uuid import UUID

from flask import Blueprint, current_app, request
from sqlalchemy import and_, select, tuple_
from sqlalchemy.exc import SQLAlchemyError

from backend.identity.audit import validate_details
from backend.identity.browser_admin import require_browser_admin_elevation
from backend.identity.elevation import AdminElevationRequired
from backend.persistence.database import DatabaseUnavailable
from backend.persistence.models.security import AuditEvent
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.pagination import InvalidCursor, decode_cursor, encode_cursor
from backend.webapp.api_v1.responses import success
from backend.webapp.web_api.middleware import (
    current_browser_actor,
    current_browser_session,
    require_browser_role,
    require_browser_session,
)


admin_audit_bp = Blueprint("web_admin_audit", __name__)
_FILTERS = frozenset({
    "occurred_at_from", "occurred_at_to", "actor_account_id",
    "actor_staff_member_id", "action_family", "target_type", "target_id", "result",
})
_ACTION_FAMILY = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_DETAIL_FIELDS = frozenset({
    "persistent", "reason", "lock_minutes", "session_count", "purpose",
    "target_staff_id", "target_account_id", "role", "old_role", "new_role",
    "handoff_id", "browser_session_id", "operation_id", "approval_reference_sha256",
    "incident_id", "revision_number", "source_revision_number", "changed_fields",
    "old_status", "new_status", "report_id", "report_type", "export_id",
    "export_format", "job_id", "job_type", "latency_ms", "result_code",
    "question_sha256", "document_count", "filters", "result_count", "report_count",
    "event_count", "old_owner_staff_id", "new_owner_staff_id",
    "incident_revision_number", "packet_item_id", "document_action",
    "record_id", "kind", "paperwork_action",
})


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


def _cursor_key() -> str:
    key = current_app.config["IDENTITY_SETTINGS"].cursor_signing_key
    if not key:
        raise ApiError(
            "dependency_unavailable", "Audit pagination is temporarily unavailable.",
            status=503, retryable=True,
        )
    return key


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        raise ApiError("validation_failed", "Audit filters are invalid.", status=400) from None
    if parsed.tzinfo is None:
        raise ApiError("validation_failed", "Audit filters are invalid.", status=400)
    return parsed.astimezone(UTC)


def _parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except (TypeError, ValueError):
        raise ApiError("validation_failed", "Audit filters are invalid.", status=400) from None


def _read_filters() -> dict[str, object]:
    raw = {
        key: value for key, value in request.args.items()
        if key not in {"cursor", "limit"}
    }
    if not set(raw) <= _FILTERS:
        raise ApiError("validation_failed", "Audit filters are invalid.", status=400)
    filters: dict[str, object] = {}
    for key, value in raw.items():
        if not value:
            raise ApiError("validation_failed", "Audit filters are invalid.", status=400)
        if key in {"occurred_at_from", "occurred_at_to"}:
            filters[key] = _parse_timestamp(value)
        elif key in {"actor_account_id", "actor_staff_member_id", "target_id"}:
            filters[key] = _parse_uuid(value)
        elif key == "result":
            if value not in {"success", "denied", "failed"}:
                raise ApiError("validation_failed", "Audit filters are invalid.", status=400)
            filters[key] = value
        elif key == "action_family":
            if not _ACTION_FAMILY.fullmatch(value):
                raise ApiError("validation_failed", "Audit filters are invalid.", status=400)
            filters[key] = value
        elif len(value) > 120:
            raise ApiError("validation_failed", "Audit filters are invalid.", status=400)
        else:
            filters[key] = value
    if (
        "occurred_at_from" in filters and "occurred_at_to" in filters
        and filters["occurred_at_from"] > filters["occurred_at_to"]
    ):
        raise ApiError("validation_failed", "Audit filters are invalid.", status=400)
    return filters


def _statement(filters: dict[str, object]):
    clauses = []
    for key, value in filters.items():
        if key == "occurred_at_from":
            clauses.append(AuditEvent.occurred_at >= value)
        elif key == "occurred_at_to":
            clauses.append(AuditEvent.occurred_at <= value)
        elif key == "action_family":
            clauses.append(AuditEvent.action.like(f"{value}.%"))
        else:
            clauses.append(getattr(AuditEvent, key) == value)
    statement = select(AuditEvent)
    if clauses:
        statement = statement.where(and_(*clauses))
    return statement.order_by(AuditEvent.occurred_at, AuditEvent.id)


def _safe_details(row: AuditEvent) -> dict:
    details = dict(row.details or {})
    if not set(details) <= _DETAIL_FIELDS:
        return {}
    try:
        return validate_details(row.action, details)
    except ValueError:
        return {}


def _event(row: AuditEvent) -> dict[str, object]:
    return {
        "event_id": str(row.id),
        "occurred_at": row.occurred_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "actor_account_id": str(row.actor_account_id) if row.actor_account_id else None,
        "actor_staff_member_id": (
            str(row.actor_staff_member_id) if row.actor_staff_member_id else None
        ),
        "action": row.action,
        "target_type": row.target_type,
        "target_id": str(row.target_id) if row.target_id else None,
        "result": row.result,
        "request_id": row.request_id,
        "client_version": row.client_version,
        "details": _safe_details(row),
    }


def _limit() -> int:
    raw = request.args.get("limit", "50")
    if not raw.isascii() or not raw.isdigit() or str(int(raw)) != raw:
        raise ApiError("validation_failed", "Audit pagination is invalid.", status=400)
    value = int(raw)
    if not 1 <= value <= 100:
        raise ApiError("validation_failed", "Audit pagination is invalid.", status=400)
    return value


@admin_audit_bp.get("/audit", endpoint="list_events")
@require_browser_session
@require_browser_role("admin")
def list_events_route():
    _require_elevation()
    filters = _read_filters()
    try:
        limit = _limit()
        raw_cursor = request.args.get("cursor")
        cursor = decode_cursor(raw_cursor, _cursor_key()) if raw_cursor else None
        statement = _statement(filters)
        if cursor:
            occurred = _parse_timestamp(str(cursor.get("created_at", "")))
            event_id = _parse_uuid(str(cursor.get("id", "")))
            statement = statement.where(
                tuple_(AuditEvent.occurred_at, AuditEvent.id) > tuple_(occurred, event_id)
            )
        rows = list(current_browser_session().scalars(statement.limit(limit + 1)))
    except ApiError:
        raise
    except InvalidCursor:
        raise ApiError("validation_failed", "Audit pagination is invalid.", status=400) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable", "Audit data is temporarily unavailable.",
            status=503, retryable=True,
        ) from None
    page = rows[:limit]
    next_cursor = None
    if len(rows) > limit and page:
        last = page[-1]
        next_cursor = encode_cursor({
            "created_at": last.occurred_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "id": str(last.id),
        }, _cursor_key())
    return success({"items": [_event(row) for row in page], "next_cursor": next_cursor})


@admin_audit_bp.get("/audit/<uuid:event_id>", endpoint="event_detail")
@require_browser_session
@require_browser_role("admin")
def event_detail_route(event_id: UUID):
    _require_elevation()
    try:
        row = current_browser_session().get(AuditEvent, event_id)
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable", "Audit data is temporarily unavailable.",
            status=503, retryable=True,
        ) from None
    if row is None:
        raise ApiError("not_found", "Audit event not found.", status=404)
    return success(_event(row))