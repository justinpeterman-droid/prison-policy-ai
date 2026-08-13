"""Elevated, privacy-preserving audit oversight endpoints."""

from __future__ import annotations

import csv
import base64
import hashlib
import io
from datetime import UTC, datetime
import re
from uuid import UUID

from flask import Blueprint, current_app, g, request
from sqlalchemy import Select, and_, literal, select, tuple_
from sqlalchemy.exc import SQLAlchemyError

from backend.persistence.database import DatabaseUnavailable
from backend.persistence.models import AuditEvent
from backend.identity.audit import AuditEventInput, validate_details
from backend.identity.elevation import StepUpRequired, consume_step_up
from backend.identity.idempotency import (
    IdempotencyConflict,
    RequestInProgress,
    claim_idempotency,
    complete_idempotency,
    request_digest,
)
from backend.webapp.api_v1.client_policy import require_compatible_write
from backend.webapp.api_v1.context import request_id
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.middleware import (
    current_actor,
    current_request_session,
    require_access_token,
    require_admin_elevation,
    require_role,
)
from backend.webapp.api_v1.pagination import (
    InvalidCursor,
    decode_cursor,
    encode_cursor,
    parse_page_size,
)
from backend.webapp.api_v1.responses import success


admin_audit_bp = Blueprint("admin_audit_api", __name__)
_FILTERS = frozenset(
    {
        "occurred_at_from",
        "occurred_at_to",
        "actor_account_id",
        "actor_staff_member_id",
        "action_family",
        "target_type",
        "target_id",
        "result",
    }
)
_ACTION_FAMILY = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_CSV_COLUMNS = (
    "event_id",
    "occurred_at",
    "actor_account_id",
    "actor_staff_member_id",
    "action",
    "target_type",
    "target_id",
    "result",
)
_DETAIL_FIELDS = frozenset(
    {
        "persistent",
        "reason",
        "lock_minutes",
        "session_count",
        "purpose",
        "target_staff_id",
        "target_account_id",
        "role",
        "old_role",
        "new_role",
        "handoff_id",
        "browser_session_id",
        "operation_id",
        "approval_reference_sha256",
        "incident_id",
        "revision_number",
        "source_revision_number",
        "changed_fields",
        "old_status",
        "new_status",
        "report_id",
        "report_type",
        "export_id",
        "export_format",
        "job_id",
        "job_type",
        "latency_ms",
        "result_code",
        "question_sha256",
        "document_count",
        "filters",
        "result_count",
        "report_count",
        "event_count",
        "old_owner_staff_id",
        "new_owner_staff_id",
    }
)


def _cursor_key() -> str:
    from flask import current_app

    key = current_app.config["IDENTITY_SETTINGS"].cursor_signing_key
    if not key:
        raise ApiError(
            "dependency_unavailable",
            "Pagination is temporarily unavailable.",
            status=503,
            retryable=True,
        )
    return key


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(UTC)
    except (TypeError, ValueError):
        raise ApiError("validation_failed", "Audit filters are invalid.", status=400) from None


def _parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except (TypeError, ValueError):
        raise ApiError("validation_failed", "Audit filters are invalid.", status=400) from None


def _read_filters(source: dict[str, str]) -> dict[str, object]:
    if not set(source) <= _FILTERS:
        raise ApiError("validation_failed", "Audit filters are invalid.", status=400)
    filters: dict[str, object] = {}
    for key, value in source.items():
        if not isinstance(value, str) or not value:
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
    return filters


def _body_filters(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not set(value) <= _FILTERS:
        raise ApiError("validation_failed", "Audit export input is invalid.", status=400)
    return _read_filters({key: str(item) for key, item in value.items()})


def _statement(filters: dict[str, object]) -> Select:
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
    """Fail closed for historical/unrecognized details before leaving the API."""
    details = dict(row.details or {})
    if not set(details) <= _DETAIL_FIELDS:
        return {}
    try:
        return validate_details(row.action, details)
    except ValueError:
        return {}


def _event(row: AuditEvent) -> dict[str, object]:
    """Return only the immutable event representation that Access may display."""
    return {
        "event_id": str(row.id),
        "occurred_at": row.occurred_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "actor_account_id": str(row.actor_account_id) if row.actor_account_id else None,
        "actor_staff_member_id": str(row.actor_staff_member_id) if row.actor_staff_member_id else None,
        "action": row.action,
        "target_type": row.target_type,
        "target_id": str(row.target_id) if row.target_id else None,
        "result": row.result,
        "details": _safe_details(row),
    }


def _csv(rows: list[AuditEvent]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=_CSV_COLUMNS, lineterminator="\r\n")
    writer.writeheader()
    for row in rows:
        data = _event(row)
        writer.writerow({name: data[name] for name in _CSV_COLUMNS})
    return stream.getvalue().encode("utf-8")


def _selection_statement(filters: dict[str, object], reference: dict[str, object] | None = None) -> Select:
    statement = _statement(filters)
    if reference is not None:
        try:
            occurred = _parse_timestamp(str(reference["selection_end_occurred_at"]))
            event_id = _parse_uuid(str(reference["selection_end_event_id"]))
        except (KeyError, TypeError):
            raise ApiError(
                "idempotent_response_unavailable",
                "Create a new export request.",
                status=409,
            ) from None
        statement = statement.where(
            tuple_(AuditEvent.occurred_at, AuditEvent.id) <= tuple_(literal(occurred), literal(event_id))
        )
    return statement


@admin_audit_bp.get("/audit-events", endpoint="list_events")
@require_access_token
@require_role("admin")
@require_admin_elevation
def list_events():
    raw = {key: value for key, value in request.args.items() if key not in {"cursor", "limit"}}
    filters = _read_filters(raw)
    try:
        limit = parse_page_size(request.args.get("limit", "50"))
        cursor = request.args.get("cursor")
        cursor_data = decode_cursor(cursor, _cursor_key()) if cursor else None
        statement = _statement(filters)
        if cursor_data:
            occurred = _parse_timestamp(str(cursor_data.get("occurred_at", "")))
            event_id = _parse_uuid(str(cursor_data.get("event_id", "")))
            statement = statement.where(
                tuple_(AuditEvent.occurred_at, AuditEvent.id) > tuple_(literal(occurred), literal(event_id))
            )
        rows = list(current_request_session().scalars(statement.limit(limit + 1)))
    except (InvalidCursor, ValueError):
        raise ApiError("validation_failed", "Pagination input is invalid.", status=400) from None
    except (DatabaseUnavailable, SQLAlchemyError):
        g.identity_db_failed = True
        raise ApiError(
            "dependency_unavailable",
            "Audit data is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    page, extra = rows[:limit], len(rows) > limit
    next_cursor = None
    if extra:
        last = page[-1]
        next_cursor = encode_cursor(
            {
                "occurred_at": last.occurred_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                "event_id": str(last.id),
            },
            _cursor_key(),
        )
    return success({"items": [_event(row) for row in page], "next_cursor": next_cursor})


@admin_audit_bp.post("/audit-events/export", endpoint="export_events")
@require_access_token
@require_role("admin")
@require_compatible_write
@require_admin_elevation
def export_events():
    """Produce a one-time, fixed-column audit CSV after Admin step-up."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {"filters", "format", "reason"}:
        raise ApiError("validation_failed", "Audit export input is invalid.", status=400)
    if (
        payload["format"] != "csv"
        or not isinstance(payload["reason"], str)
        or not payload["reason"].strip()
        or len(payload["reason"]) > 500
    ):
        raise ApiError("validation_failed", "Audit export input is invalid.", status=400)
    filters = _body_filters(payload["filters"])
    key = request.headers.get("Idempotency-Key", "")
    if not key:
        raise ApiError("validation_failed", "Idempotency-Key is required.", status=400)
    actor = current_actor()
    db = current_request_session()
    canonical = {
        "filters": {key: str(value) for key, value in sorted(filters.items())},
        "format": "csv",
        "reason": payload["reason"],
    }
    try:
        claim = claim_idempotency(
            db,
            actor,
            key=key,
            action="admin.audit_export",
            request_sha256=request_digest(canonical),
            now=datetime.now(UTC),
        )
        pending = request.headers.get("X-Admin-Step-Up", "")
        try:
            consume_step_up(
                db,
                actor=actor,
                raw_token=pending,
                purpose="audit_export",
                now=datetime.now(UTC),
            )
        except (StepUpRequired, ValueError):
            raise ApiError(
                "step_up_required",
                "Administrator PIN confirmation is required.",
                status=403,
            ) from None
        rows = list(
            db.scalars(
                _selection_statement(filters, claim.response_reference if claim.replayed else None).limit(10_001)
            )
        )
        if len(rows) > 10_000:
            raise ApiError(
                "audit_export_limit_exceeded",
                "Narrow the audit filters before exporting.",
                status=409,
            )
        export_id = str((claim.response_reference or {}).get("export_id", claim.record_id))
        data = _csv(rows)
        if not claim.replayed:
            current_app.config["AUDIT_WRITER"].append(
                db,
                AuditEventInput(
                    actor_account_id=actor.account_id,
                    actor_staff_member_id=actor.staff_member_id,
                    action="admin.audit_exported",
                    result="success",
                    request_id=request_id(),
                    target_type="audit_export",
                    target_id=None,
                    details={"export_id": export_id, "event_count": len(rows)},
                    client_version=str(g.client_version),
                ),
            )
            if rows:
                last = rows[-1]
                reference = {
                    "export_id": export_id,
                    "selection_end_occurred_at": last.occurred_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                    "selection_end_event_id": str(last.id),
                }
            else:
                reference = {
                    "export_id": export_id,
                    "selection_end_occurred_at": "1970-01-01T00:00:00Z",
                    "selection_end_event_id": "00000000-0000-0000-0000-000000000000",
                }
            complete_idempotency(
                db,
                claim,
                response_status=200,
                response_reference=reference,
                now=datetime.now(UTC),
            )
        digest = base64.b64encode(hashlib.sha256(data).digest()).decode("ascii")
    except (IdempotencyConflict, RequestInProgress) as error:
        code = "request_in_progress" if isinstance(error, RequestInProgress) else "idempotency_conflict"
        raise ApiError(code, "The export request conflicts with an existing request.", status=409) from None
    except ValueError:
        raise ApiError("validation_failed", "Audit export input is invalid.", status=400) from None
    except (DatabaseUnavailable, SQLAlchemyError):
        g.identity_db_failed = True
        raise ApiError(
            "dependency_unavailable",
            "Audit export is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    response = current_app.response_class(data, mimetype="text/csv")
    response.headers["Content-Disposition"] = f'attachment; filename="audit-events-{export_id}.csv"'
    response.headers["Digest"] = f"sha-256={digest}"
    response.headers["X-Export-ID"] = export_id
    response.headers["X-Audit-Row-Count"] = str(len(rows))
    response.headers["X-Request-ID"] = request_id()
    response.headers["Cache-Control"] = "no-store"
    return response
