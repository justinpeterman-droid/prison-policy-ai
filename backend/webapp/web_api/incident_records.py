"""Cookie-authenticated incident create, edit, history, and restore routes."""
from datetime import UTC
import json
from uuid import UUID

from flask import Blueprint, current_app, request
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from backend.identity.idempotency import IdempotencyConflict, RequestInProgress
from backend.persistence.database import DatabaseUnavailable
from backend.persistence.models.identity import StaffMember
from backend.reports.persistence import (
    IncidentNotFound,
    IncidentRevisionNotFound,
    IncidentView,
    create_incident,
    get_incident,
    get_incident_revision,
    incident_revision_content,
    list_incident_revisions,
    restore_incident_record,
    save_incident_record,
)
from backend.reports.revisions import RevisionConflict
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.pagination import InvalidCursor, decode_cursor, encode_cursor
from backend.webapp.api_v1.responses import success
from backend.webapp.api_v1.schemas.reporting import SaveIncidentRequest
from backend.webapp.web_api.common import (
    LOCK_CONFLICT_STATES,
    json_body,
    request_metadata,
    require_idempotency_key,
    timestamp,
    validate_if_match,
)
from backend.webapp.web_api.middleware import (
    current_browser_actor,
    current_browser_session,
    require_browser_csrf,
    require_browser_session,
)


incident_records_bp = Blueprint("web_incident_records", __name__)

_CONTENT_FIELDS = {
    "schema_version",
    "incident_number",
    "incident_name",
    "field_notes",
    "incident_date",
    "incident_time",
    "facility",
    "shift",
    "location",
    "category",
    "classification",
    "extracted_facts",
    "gap_answers",
    "charges",
    "validation",
    "warnings",
}
_CREATE_FIELDS = {*_CONTENT_FIELDS, "reporting_staff_ids"}
_SAVE_FIELDS = {*_CONTENT_FIELDS, "base_revision_number", "reason"}


def _staff_data(db, staff_ids: tuple[UUID, ...]) -> list[dict[str, str | None]]:
    if not staff_ids:
        return []
    rows = list(db.query(StaffMember).filter(StaffMember.id.in_(staff_ids)).all())
    by_id = {row.id: row for row in rows}
    result: list[dict[str, str | None]] = []
    for staff_id in staff_ids:
        row = by_id.get(staff_id)
        if row is None:
            raise RuntimeError("incident reporting officer is unavailable")
        result.append({
            "staff_id": str(row.id),
            "employee_number": row.employee_number,
            "display_name": " ".join(
                part for part in (row.rank, row.first_name, row.last_name) if part
            ),
            "rank": row.rank,
            "shift": row.shift,
        })
    return result


def _view_data(db, view: IncidentView) -> dict[str, object]:
    row = view.incident
    content = view.content or {
        "incident_number": row.incident_number,
        "incident_name": row.incident_name,
        "field_notes": row.field_notes,
        "incident_date": row.incident_date,
        "incident_time": row.incident_time,
        "facility": row.facility,
        "shift": row.shift,
        "location": row.location,
        "category": row.category,
        "classification": row.classification,
        "extracted_facts": row.extracted_facts,
        "gap_answers": row.gap_answers,
        "charges": row.charges,
        "validation": row.validation,
        "warnings": [],
    }
    incident_date = content.get("incident_date")
    incident_time = content.get("incident_time")
    return {
        "incident_id": str(row.id),
        "incident_number": content.get("incident_number"),
        "incident_name": content.get("incident_name"),
        "status": view.status or row.status,
        "current_revision_number": view.revision_number
        or row.current_revision_number,
        "reporting_staff_ids": [str(value) for value in view.reporting_staff_ids],
        "reporting_officers": _staff_data(db, view.reporting_staff_ids),
        "field_notes": content.get("field_notes", ""),
        "incident_date": (
            incident_date.isoformat()
            if hasattr(incident_date, "isoformat")
            else incident_date
        ),
        "incident_time": (
            incident_time.isoformat()
            if hasattr(incident_time, "isoformat")
            else incident_time
        ),
        "facility": content.get("facility"),
        "shift": content.get("shift"),
        "location": content.get("location"),
        "category": content.get("category"),
        "classification": content.get("classification", {}),
        "extracted_facts": content.get("extracted_facts", {}),
        "gap_answers": content.get("gap_answers", {}),
        "charges": content.get("charges", []),
        "validation": content.get("validation", {}),
        "warnings": content.get("warnings", []),
        "created_at": timestamp(row.created_at),
        "updated_at": timestamp(view.updated_at or row.updated_at),
    }


def _revision_summary(row) -> dict[str, object]:
    return {
        "revision_id": str(row.id),
        "revision_number": row.revision_number,
        "reason": row.reason,
        "changed_fields": list((row.changed_fields or {}).get("fields", [])),
        "editor_staff_member_id": str(row.editor_staff_member_id),
        "client_version": row.client_version,
        "created_at": timestamp(row.created_at),
    }


def _constraint_name(error: IntegrityError) -> str | None:
    diagnostic = getattr(getattr(error, "orig", None), "diag", None)
    return getattr(diagnostic, "constraint_name", None)


def _write(operation, *, status: int = 200):
    db = current_browser_session()
    try:
        view = operation(db)
        db.commit()
        return success(_view_data(db, view), status=status)
    except RequestInProgress as error:
        db.rollback()
        raise ApiError(
            "request_in_progress", str(error), status=409, retryable=True
        ) from None
    except IdempotencyConflict as error:
        db.rollback()
        raise ApiError("idempotency_conflict", str(error), status=409) from None
    except RevisionConflict as error:
        db.rollback()
        raise ApiError(
            "revision_conflict",
            "The incident changed; your local text has been preserved.",
            status=409,
            details={"current_revision_number": error.current_revision_number},
        ) from None
    except (IncidentNotFound, IncidentRevisionNotFound):
        db.rollback()
        raise ApiError("not_found", "Incident not found.", status=404) from None
    except (ValidationError, ValueError, TypeError):
        db.rollback()
        raise ApiError(
            "validation_failed", "The incident request is invalid.", status=400
        ) from None
    except IntegrityError as error:
        db.rollback()
        if _constraint_name(error) == "uq_incidents_incident_number":
            raise ApiError(
                "incident_number_conflict",
                "This incident number is already in use.",
                status=409,
            ) from None
        raise ApiError(
            "revision_conflict",
            "The incident changed; your local text has been preserved.",
            status=409,
        ) from None
    except OperationalError as error:
        db.rollback()
        sqlstate = getattr(getattr(error, "orig", None), "sqlstate", None)
        if sqlstate in LOCK_CONFLICT_STATES:
            raise ApiError(
                "revision_conflict",
                "The incident changed; your local text has been preserved.",
                status=409,
            ) from None
        raise ApiError(
            "dependency_unavailable",
            "Incident storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db.rollback()
        raise ApiError(
            "dependency_unavailable",
            "Incident storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@incident_records_bp.post("/incidents")
@require_browser_session
@require_browser_csrf
def create_incident_route():
    payload = json_body(
        allowed=_CREATE_FIELDS,
        required={"reporting_staff_ids", "field_notes"},
        message="The incident request is invalid.",
    )
    try:
        reporting_staff_ids = payload["reporting_staff_ids"]
        if not isinstance(reporting_staff_ids, list):
            raise ValueError
        content = {
            key: value for key, value in payload.items() if key != "reporting_staff_ids"
        }
        content["base_revision_number"] = 0
        content["reason"] = "manual_save"
        model = SaveIncidentRequest.model_validate_json(json.dumps(content))
    except (ValidationError, ValueError, TypeError):
        raise ApiError(
            "validation_failed", "The incident request is invalid.", status=400
        ) from None
    req_id, version = request_metadata()
    return _write(
        lambda db: create_incident(
            db,
            current_browser_actor(),
            reporting_staff_ids,
            model,
            require_idempotency_key(),
            request_id=req_id,
            client_version=version,
            audit_writer=current_app.config["AUDIT_WRITER"],
        ),
        status=201,
    )


@incident_records_bp.get("/incidents/<uuid:incident_id>")
@require_browser_session
def get_incident_route(incident_id: UUID):
    try:
        db = current_browser_session()
        return success(_view_data(
            db, get_incident(db, current_browser_actor(), incident_id)
        ))
    except IncidentNotFound:
        raise ApiError("not_found", "Incident not found.", status=404) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Incident storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@incident_records_bp.patch("/incidents/<uuid:incident_id>")
@require_browser_session
@require_browser_csrf
def save_incident_route(incident_id: UUID):
    payload = json_body(
        allowed=_SAVE_FIELDS,
        required={"field_notes", "base_revision_number"},
        message="The incident request is invalid.",
    )
    try:
        model = SaveIncidentRequest.model_validate_json(json.dumps(payload))
    except ValidationError:
        raise ApiError(
            "validation_failed", "The incident request is invalid.", status=400
        ) from None
    validate_if_match(model.base_revision_number)
    req_id, version = request_metadata()
    return _write(lambda db: save_incident_record(
        db,
        current_browser_actor(),
        incident_id,
        model,
        require_idempotency_key(),
        request_id=req_id,
        client_version=version,
        audit_writer=current_app.config["AUDIT_WRITER"],
    ))


@incident_records_bp.get("/incidents/<uuid:incident_id>/revisions")
@require_browser_session
def list_incident_revisions_route(incident_id: UUID):
    try:
        if not set(request.args) <= {"limit", "cursor"}:
            raise ValueError
        raw_limit = request.args.get("limit", "100")
        limit = int(raw_limit)
        if str(limit) != raw_limit.strip() or not 1 <= limit <= 100:
            raise ValueError
        key = current_app.config["IDENTITY_SETTINGS"].cursor_signing_key
        if not key:
            raise RuntimeError("incident pagination key is unavailable")
        raw_cursor = request.args.get("cursor")
        cursor = decode_cursor(raw_cursor, key) if raw_cursor else None
        page = list_incident_revisions(
            current_browser_session(),
            current_browser_actor(),
            incident_id,
            limit=limit,
            cursor=cursor,
        )
        return success({
            "items": [_revision_summary(row) for row in page.items],
            "next_cursor": encode_cursor(page.next_cursor, key)
            if page.next_cursor
            else None,
        })
    except (InvalidCursor, ValueError):
        raise ApiError(
            "validation_failed", "Revision pagination is invalid.", status=400
        ) from None
    except IncidentNotFound:
        raise ApiError("not_found", "Incident not found.", status=404) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Incident storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@incident_records_bp.get(
    "/incidents/<uuid:incident_id>/revisions/<int:revision_number>"
)
@require_browser_session
def get_incident_revision_route(incident_id: UUID, revision_number: int):
    try:
        row = get_incident_revision(
            current_browser_session(),
            current_browser_actor(),
            incident_id,
            revision_number,
        )
        return success({**_revision_summary(row), **incident_revision_content(row)})
    except (IncidentNotFound, IncidentRevisionNotFound):
        raise ApiError("not_found", "Incident not found.", status=404) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Incident storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@incident_records_bp.post("/incidents/<uuid:incident_id>/restore")
@require_browser_session
@require_browser_csrf
def restore_incident_route(incident_id: UUID):
    payload = json_body(
        exact={"revision_number"}, message="The restore request is invalid."
    )
    revision_number = payload["revision_number"]
    if not isinstance(revision_number, int) or isinstance(revision_number, bool):
        raise ApiError(
            "validation_failed", "The restore request is invalid.", status=400
        )
    req_id, version = request_metadata()
    return _write(lambda db: restore_incident_record(
        db,
        current_browser_actor(),
        incident_id,
        revision_number,
        require_idempotency_key(),
        request_id=req_id,
        client_version=version,
        audit_writer=current_app.config["AUDIT_WRITER"],
    ))
