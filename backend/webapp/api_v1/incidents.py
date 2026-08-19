"""Authorized incident workspace and immutable revision routes."""
from datetime import UTC
import json
from uuid import UUID

from flask import Blueprint, current_app, g, request
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from backend.identity.idempotency import IdempotencyConflict, RequestInProgress
from backend.persistence.database import DatabaseUnavailable
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
from backend.webapp.api_v1.client_policy import require_compatible_write
from backend.webapp.api_v1.context import request_id
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.middleware import (
    current_actor,
    current_request_session,
    require_access_token,
)
from backend.webapp.api_v1.pagination import (
    InvalidCursor,
    decode_cursor,
    encode_cursor,
    parse_page_size,
)
from backend.webapp.api_v1.responses import success
from backend.webapp.api_v1.schemas.reporting import SaveIncidentRequest


incidents_bp = Blueprint("incidents_api", __name__)
CREATE_REQUIRED_FIELDS = {"reporting_staff_ids", "field_notes"}
CREATE_FIELDS = {
    *CREATE_REQUIRED_FIELDS,
    "incident_number",
    "incident_name",
}
SAVE_FIELDS = {
    "schema_version", "incident_number", "incident_name", "field_notes",
    "incident_date", "incident_time", "facility", "shift", "location", "category",
    "classification", "extracted_facts", "gap_answers", "charges", "validation",
    "warnings", "base_revision_number", "reason",
}


def _body(*, exact: set[str] | None = None, allowed: set[str] | None = None) -> dict:
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise ApiError("validation_failed", "The request body is invalid.", status=400)
    keys = set(value)
    if (exact is not None and keys != exact) or (
        allowed is not None and (not keys or not keys <= allowed)
    ):
        raise ApiError("validation_failed", "The request body is invalid.", status=400)
    return value


def _metadata() -> tuple[str, str]:
    return request_id(), str(g.client_version)


def _validate_if_match(base_revision_number: int) -> None:
    value = request.headers.get("If-Match")
    if value is None:
        return
    if (
        len(value) < 3 or value[0] != '"' or value[-1] != '"'
        or not value[1:-1].isdigit() or value[1:-1].startswith("0")
        or int(value[1:-1]) != base_revision_number
    ):
        raise ApiError(
            "validation_failed", "If-Match must agree with base_revision_number.",
            status=400,
        )


def _timestamp(value) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _view_data(view: IncidentView) -> dict[str, object]:
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
    }
    incident_date = content.get("incident_date")
    incident_time = content.get("incident_time")
    return {
        "incident_id": str(row.id),
        "incident_number": content.get("incident_number"),
        "incident_name": content.get("incident_name"),
        "status": view.status or row.status,
        "current_revision_number": view.revision_number or row.current_revision_number,
        "reporting_staff_ids": [str(value) for value in view.reporting_staff_ids],
        "field_notes": content.get("field_notes", ""),
        "incident_date": (
            incident_date.isoformat()
            if hasattr(incident_date, "isoformat") else incident_date
        ),
        "incident_time": (
            incident_time.isoformat()
            if hasattr(incident_time, "isoformat") else incident_time
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
        "created_at": _timestamp(row.created_at),
        "updated_at": _timestamp(view.updated_at or row.updated_at),
    }


def _revision_summary(row) -> dict[str, object]:
    return {
        "revision_number": row.revision_number,
        "reason": row.reason,
        "changed_fields": list((row.changed_fields or {}).get("fields", [])),
        "editor_staff_member_id": str(row.editor_staff_member_id),
        "client_version": row.client_version,
        "created_at": _timestamp(row.created_at),
    }


def _revision_data(row) -> dict[str, object]:
    return {**_revision_summary(row), **incident_revision_content(row)}


def _constraint_name(error: IntegrityError) -> str | None:
    diagnostic = getattr(getattr(error, "orig", None), "diag", None)
    return getattr(diagnostic, "constraint_name", None)


def _handle_write(operation):
    db = current_request_session()
    try:
        result, status = operation(db)
        db.commit()
        return success(_view_data(result), status=status)
    except RequestInProgress as error:
        db.rollback()
        raise ApiError("request_in_progress", str(error), status=409, retryable=True) from None
    except IdempotencyConflict as error:
        db.rollback()
        raise ApiError("idempotency_conflict", str(error), status=409) from None
    except RevisionConflict as error:
        db.rollback()
        raise ApiError(
            "revision_conflict", "The incident changed; reload and try again.", status=409,
            details={"current_revision_number": error.current_revision_number},
        ) from None
    except (IncidentNotFound, IncidentRevisionNotFound):
        db.rollback()
        raise ApiError("not_found", "Incident not found.", status=404) from None
    except (ValidationError, ValueError):
        db.rollback()
        raise ApiError("validation_failed", "The incident request is invalid.", status=400) from None
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
            "The incident changed; reload and try again.",
            status=409,
        ) from None
    except OperationalError as error:
        db.rollback()
        sqlstate = getattr(getattr(error, "orig", None), "sqlstate", None)
        if sqlstate in {"40P01", "40001", "55P03"}:
            raise ApiError(
                "revision_conflict", "The incident changed; reload and try again.", status=409,
            ) from None
        raise ApiError(
            "dependency_unavailable", "Incident storage is temporarily unavailable.",
            status=503, retryable=True,
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db.rollback()
        raise ApiError(
            "dependency_unavailable", "Incident storage is temporarily unavailable.",
            status=503, retryable=True,
        ) from None


@incidents_bp.post("", endpoint="create")
@require_access_token
@require_compatible_write
def create_route():
    payload = _body(allowed=CREATE_FIELDS)
    if not CREATE_REQUIRED_FIELDS <= set(payload):
        raise ApiError("validation_failed", "The incident request is invalid.", status=400)
    try:
        model = SaveIncidentRequest.model_validate({
            key: value
            for key, value in payload.items()
            if key != "reporting_staff_ids"
        })
    except ValidationError:
        raise ApiError("validation_failed", "The incident request is invalid.", status=400) from None
    req_id, version = _metadata()
    return _handle_write(lambda db: (
        create_incident(
            db, current_actor(), payload["reporting_staff_ids"], model,
            request.headers.get("Idempotency-Key", ""), request_id=req_id,
            client_version=version, audit_writer=current_app.config["AUDIT_WRITER"],
        ),
        201,
    ))


@incidents_bp.get("/<uuid:incident_id>", endpoint="get")
@require_access_token
def get_route(incident_id: UUID):
    try:
        return success(_view_data(get_incident(
            current_request_session(), current_actor(), incident_id)))
    except IncidentNotFound:
        raise ApiError("not_found", "Incident not found.", status=404) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable", "Incident storage is temporarily unavailable.",
            status=503, retryable=True,
        ) from None


@incidents_bp.patch("/<uuid:incident_id>", endpoint="save")
@require_access_token
@require_compatible_write
def save_route(incident_id: UUID):
    payload = _body(allowed=SAVE_FIELDS)
    if "field_notes" not in payload or "base_revision_number" not in payload:
        raise ApiError("validation_failed", "The incident request is invalid.", status=400)
    try:
        model = SaveIncidentRequest.model_validate_json(json.dumps(payload))
    except ValidationError:
        raise ApiError("validation_failed", "The incident request is invalid.", status=400) from None
    _validate_if_match(model.base_revision_number)
    req_id, version = _metadata()
    return _handle_write(lambda db: (
        save_incident_record(
            db, current_actor(), incident_id, model,
            request.headers.get("Idempotency-Key", ""), request_id=req_id,
            client_version=version, audit_writer=current_app.config["AUDIT_WRITER"],
        ),
        200,
    ))


@incidents_bp.get("/<uuid:incident_id>/revisions", endpoint="revision_list")
@require_access_token
def revision_list_route(incident_id: UUID):
    try:
        limit = parse_page_size(request.args.get("limit", "100"))
        key = current_app.config["IDENTITY_SETTINGS"].cursor_signing_key
        if not key:
            raise RuntimeError("incident revision pagination key is unavailable")
        raw_cursor = request.args.get("cursor")
        cursor = decode_cursor(raw_cursor, key) if raw_cursor else None
        page = list_incident_revisions(
            current_request_session(), current_actor(), incident_id,
            limit=limit, cursor=cursor,
        )
        return success({
            "items": [_revision_summary(row) for row in page.items],
            "next_cursor": encode_cursor(page.next_cursor, key) if page.next_cursor else None,
        })
    except (InvalidCursor, ValueError):
        raise ApiError("validation_failed", "Revision pagination is invalid.", status=400) from None
    except IncidentNotFound:
        raise ApiError("not_found", "Incident not found.", status=404) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable", "Incident storage is temporarily unavailable.",
            status=503, retryable=True,
        ) from None


@incidents_bp.get(
    "/<uuid:incident_id>/revisions/<int:revision_number>", endpoint="revision_detail",
)
@require_access_token
def revision_detail_route(incident_id: UUID, revision_number: int):
    try:
        row = get_incident_revision(
            current_request_session(), current_actor(), incident_id, revision_number)
        return success(_revision_data(row))
    except (IncidentNotFound, IncidentRevisionNotFound):
        raise ApiError("not_found", "Incident not found.", status=404) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable", "Incident storage is temporarily unavailable.",
            status=503, retryable=True,
        ) from None


@incidents_bp.post("/<uuid:incident_id>/restore", endpoint="restore")
@require_access_token
@require_compatible_write
def restore_route(incident_id: UUID):
    payload = _body(exact={"revision_number"})
    req_id, version = _metadata()
    return _handle_write(lambda db: (
        restore_incident_record(
            db, current_actor(), incident_id, payload["revision_number"],
            request.headers.get("Idempotency-Key", ""), request_id=req_id,
            client_version=version, audit_writer=current_app.config["AUDIT_WRITER"],
        ),
        200,
    ))
