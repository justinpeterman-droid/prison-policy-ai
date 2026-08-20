"""Cookie-authenticated operational-paperwork and NCU Count Sheet routes."""
from datetime import UTC
import json
from uuid import UUID

from flask import Blueprint, current_app, request
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from backend.identity.idempotency import IdempotencyConflict, RequestInProgress
from backend.paperwork.actions import record_paperwork_action
from backend.paperwork.count_sheet import (
    calculate_count_totals,
    count_sheet_structure,
)
from backend.paperwork.models import PaperworkKind, PaperworkView
from backend.paperwork.schemas import SavePaperworkRequest
from backend.paperwork.service import (
    PaperworkNotFound,
    PaperworkRevisionConflict,
    PaperworkRevisionNotFound,
    get_paperwork_record,
    list_paperwork_records,
    list_paperwork_revisions,
    restore_paperwork_record,
    save_paperwork_record,
)
from backend.persistence.database import DatabaseUnavailable
from backend.persistence.models.paperwork import PaperworkRevision
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.pagination import InvalidCursor, decode_cursor, encode_cursor
from backend.webapp.api_v1.responses import success
from backend.webapp.web_api.common import (
    LOCK_CONFLICT_STATES,
    json_body,
    positive_int,
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


paperwork_bp = Blueprint("web_paperwork", __name__)
_SAVE_FIELDS = {
    "schema_version",
    "work_date",
    "shift",
    "payload",
    "base_revision_number",
    "reason",
}
_ACTIONS = {"preview", "print", "download_pdf"}


def _settings_key() -> str:
    settings = current_app.config.get("IDENTITY_SETTINGS")
    key = getattr(settings, "cursor_signing_key", None)
    if not isinstance(key, str) or not key:
        raise ApiError(
            "dependency_unavailable",
            "Paperwork pagination is temporarily unavailable.",
            status=503,
            retryable=True,
        )
    return key


def _single_arg(name: str) -> str | None:
    values = request.args.getlist(name)
    if len(values) > 1:
        raise ApiError(
            "validation_failed",
            "The paperwork request is invalid.",
            status=400,
        )
    return values[0] if values else None


def _limit(default: int = 25, maximum: int = 50) -> int:
    raw = _single_arg("limit")
    if raw is None:
        return default
    if not raw.isascii() or not raw.isdigit():
        raise ValueError("paperwork page size is invalid")
    value = int(raw)
    if str(value) != raw or not 1 <= value <= maximum:
        raise ValueError("paperwork page size is invalid")
    return value


def _count_validation(payload: dict[str, object]) -> dict[str, object]:
    value = calculate_count_totals(payload)
    return {
        "row_totals": value.row_totals,
        "out_of_housing": value.out_of_housing,
        "unit_totals": value.unit_totals,
        "column_totals": value.column_totals,
        "housing_total": value.housing_total,
        "operational_total": value.operational_total,
        "difference": value.difference,
        "reconciled": value.reconciled,
    }


def _record_data(view: PaperworkView, *, include_payload: bool = True) -> dict[str, object]:
    data: dict[str, object] = {
        "record_id": str(view.record_id),
        "kind": view.kind.value,
        "work_date": view.work_date.isoformat(),
        "shift": view.shift,
        "current_revision_number": view.current_revision_number,
        "created_by_staff_member_id": str(view.created_by_staff_member_id),
        "last_editor_staff_member_id": str(view.last_editor_staff_member_id),
        "created_at": timestamp(view.created_at),
        "updated_at": timestamp(view.updated_at),
    }
    if view.kind is PaperworkKind.COUNT_SHEET:
        validation = _count_validation(view.payload)
        data["validation"] = validation if include_payload else {
            key: validation[key]
            for key in (
                "housing_total",
                "operational_total",
                "difference",
                "reconciled",
            )
        }
    if include_payload:
        data["payload"] = view.payload
    return data


def _revision_data(row) -> dict[str, object]:
    return {
        "revision_number": row.revision_number,
        "reason": row.reason,
        "changed_fields": list((row.changed_fields or {}).get("paths", [])),
        "editor_staff_member_id": str(row.editor_staff_member_id),
        "client_version": row.client_version,
        "created_at": timestamp(row.created_at),
    }


def _record_cursor(raw: str | None) -> dict[str, str] | None:
    if not raw:
        return None
    decoded = decode_cursor(raw, _settings_key())
    return {"updated_at": decoded["created_at"], "id": decoded["id"]}


def _encoded_record_cursor(cursor: dict[str, str] | None) -> str | None:
    if cursor is None:
        return None
    return encode_cursor(
        {"created_at": cursor["updated_at"], "id": cursor["id"]},
        _settings_key(),
    )


def _revision_cursor(record_id: UUID, raw: str | None) -> dict[str, str] | None:
    if not raw:
        return None
    get_paperwork_record(
        current_browser_session(),
        current_browser_actor(),
        record_id,
        expected_kind=PaperworkKind.COUNT_SHEET,
    )
    decoded = decode_cursor(raw, _settings_key())
    try:
        row = current_browser_session().get(PaperworkRevision, UUID(decoded["id"]))
    except ValueError:
        raise InvalidCursor("cursor is invalid") from None
    if (
        row is None
        or row.record_id != record_id
        or timestamp(row.created_at) != decoded["created_at"]
    ):
        raise InvalidCursor("cursor is invalid")
    return {"revision_number": str(row.revision_number), "id": str(row.id)}


def _encoded_revision_cursor(cursor: dict[str, str] | None) -> str | None:
    if cursor is None:
        return None
    row = current_browser_session().get(PaperworkRevision, UUID(cursor["id"]))
    if row is None:
        raise RuntimeError("paperwork revision cursor target is unavailable")
    return encode_cursor(
        {"created_at": timestamp(row.created_at), "id": str(row.id)},
        _settings_key(),
    )


def _validation_fields(error: ValidationError) -> list[str]:
    return sorted({
        ".".join(str(part) for part in item.get("loc", ()))[:120]
        for item in error.errors(include_input=False, include_url=False)
        if item.get("loc")
    })[:20]


def _save_model() -> SavePaperworkRequest:
    payload = json_body(
        exact=_SAVE_FIELDS,
        message="The Count Sheet request is invalid.",
    )
    try:
        return SavePaperworkRequest.model_validate_json(
            json.dumps(payload, ensure_ascii=False, allow_nan=False)
        )
    except ValidationError as error:
        raise ApiError(
            "validation_failed",
            "The Count Sheet request is invalid.",
            status=400,
            details={
                "stage": "request_schema",
                "fields": _validation_fields(error),
            },
        ) from None
    except (TypeError, ValueError):
        raise ApiError(
            "validation_failed",
            "The Count Sheet request is invalid.",
            status=400,
            details={"stage": "request_encoding"},
        ) from None


def _write(operation, *, created: bool = False):
    db = current_browser_session()
    try:
        value = operation(db)
        db.commit()
        return success(value, status=201 if created else 200)
    except RequestInProgress as error:
        db.rollback()
        raise ApiError(
            "request_in_progress", str(error), status=409, retryable=True,
        ) from None
    except IdempotencyConflict as error:
        db.rollback()
        raise ApiError("idempotency_conflict", str(error), status=409) from None
    except PaperworkRevisionConflict as error:
        db.rollback()
        raise ApiError(
            "revision_conflict",
            "The Count Sheet changed. Your local values have been preserved; reload before saving again.",
            status=409,
            details={"current_revision_number": error.current_revision_number},
        ) from None
    except (PaperworkNotFound, PaperworkRevisionNotFound):
        db.rollback()
        raise ApiError("not_found", "Count Sheet not found.", status=404) from None
    except ValidationError as error:
        db.rollback()
        raise ApiError(
            "validation_failed",
            "The Count Sheet request is invalid.",
            status=400,
            details={
                "stage": "paperwork_schema",
                "fields": _validation_fields(error),
            },
        ) from None
    except ValueError:
        db.rollback()
        raise ApiError(
            "validation_failed",
            "The Count Sheet request is invalid.",
            status=400,
            details={"stage": "paperwork_rule"},
        ) from None
    except TypeError:
        db.rollback()
        raise ApiError(
            "validation_failed",
            "The Count Sheet request is invalid.",
            status=400,
            details={"stage": "paperwork_type"},
        ) from None
    except IntegrityError:
        db.rollback()
        raise ApiError(
            "revision_conflict",
            "The Count Sheet changed. Your local values have been preserved; reload before saving again.",
            status=409,
        ) from None
    except OperationalError as error:
        db.rollback()
        state = getattr(getattr(error, "orig", None), "sqlstate", None)
        if state in LOCK_CONFLICT_STATES:
            raise ApiError(
                "revision_conflict",
                "The Count Sheet changed. Your local values have been preserved; reload before saving again.",
                status=409,
            ) from None
        raise ApiError(
            "dependency_unavailable",
            "Count Sheet storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db.rollback()
        raise ApiError(
            "dependency_unavailable",
            "Count Sheet storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@paperwork_bp.get("/paperwork")
@require_browser_session
def list_route():
    if set(request.args) - {"kind", "limit", "cursor"}:
        raise ApiError("validation_failed", "The paperwork request is invalid.", status=400)
    kind = _single_arg("kind")
    if kind != PaperworkKind.COUNT_SHEET.value:
        raise ApiError("validation_failed", "The paperwork request is invalid.", status=400)
    try:
        page = list_paperwork_records(
            current_browser_session(),
            current_browser_actor(),
            kind=PaperworkKind.COUNT_SHEET,
            limit=_limit(),
            cursor=_record_cursor(_single_arg("cursor")),
        )
        return success({
            "items": [_record_data(item, include_payload=False) for item in page.items],
            "next_cursor": _encoded_record_cursor(page.next_cursor),
        })
    except (InvalidCursor, ValueError):
        raise ApiError(
            "validation_failed", "Paperwork pagination is invalid.", status=400,
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Count Sheet storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@paperwork_bp.get("/paperwork/count-sheets/structure")
@require_browser_session
def structure_route():
    return success(count_sheet_structure())


@paperwork_bp.post("/paperwork/count-sheets")
@require_browser_session
@require_browser_csrf
def create_route():
    model = _save_model()
    req_id, version = request_metadata()
    return _write(
        lambda db: _record_data(save_paperwork_record(
            db,
            current_browser_actor(),
            kind=PaperworkKind.COUNT_SHEET,
            request_model=model,
            idempotency_key=require_idempotency_key(),
            request_id=req_id,
            client_version=version,
            audit_writer=current_app.config["AUDIT_WRITER"],
        )),
        created=True,
    )


@paperwork_bp.get("/paperwork/count-sheets/<uuid:record_id>")
@require_browser_session
def get_route(record_id: UUID):
    try:
        return success(_record_data(get_paperwork_record(
            current_browser_session(),
            current_browser_actor(),
            record_id,
            expected_kind=PaperworkKind.COUNT_SHEET,
        )))
    except PaperworkNotFound:
        raise ApiError("not_found", "Count Sheet not found.", status=404) from None
    except (ValidationError, ValueError):
        raise ApiError(
            "dependency_unavailable", "The saved Count Sheet is invalid.", status=503,
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Count Sheet storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@paperwork_bp.patch("/paperwork/count-sheets/<uuid:record_id>")
@require_browser_session
@require_browser_csrf
def save_route(record_id: UUID):
    model = _save_model()
    if model.base_revision_number is None:
        raise ApiError(
            "validation_failed",
            "An existing Count Sheet requires a base revision.",
            status=400,
        )
    validate_if_match(model.base_revision_number)
    req_id, version = request_metadata()
    return _write(lambda db: _record_data(save_paperwork_record(
        db,
        current_browser_actor(),
        record_id=record_id,
        kind=PaperworkKind.COUNT_SHEET,
        request_model=model,
        idempotency_key=require_idempotency_key(),
        request_id=req_id,
        client_version=version,
        audit_writer=current_app.config["AUDIT_WRITER"],
    )))


@paperwork_bp.get("/paperwork/count-sheets/<uuid:record_id>/revisions")
@require_browser_session
def revisions_route(record_id: UUID):
    if set(request.args) - {"limit", "cursor"}:
        raise ApiError("validation_failed", "The revision request is invalid.", status=400)
    try:
        page = list_paperwork_revisions(
            current_browser_session(),
            current_browser_actor(),
            record_id,
            limit=_limit(),
            cursor=_revision_cursor(record_id, _single_arg("cursor")),
            expected_kind=PaperworkKind.COUNT_SHEET,
        )
        return success({
            "items": [_revision_data(item) for item in page.items],
            "next_cursor": _encoded_revision_cursor(page.next_cursor),
        })
    except PaperworkNotFound:
        raise ApiError("not_found", "Count Sheet not found.", status=404) from None
    except (InvalidCursor, ValueError):
        raise ApiError("validation_failed", "Revision pagination is invalid.", status=400) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Count Sheet revisions are temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@paperwork_bp.post("/paperwork/count-sheets/<uuid:record_id>/restore")
@require_browser_session
@require_browser_csrf
def restore_route(record_id: UUID):
    payload = json_body(
        exact={"revision_number"},
        message="The restore request is invalid.",
    )
    req_id, version = request_metadata()
    return _write(lambda db: _record_data(restore_paperwork_record(
        db,
        current_browser_actor(),
        record_id=record_id,
        source_revision_number=positive_int(
            payload.get("revision_number"), name="revision_number"
        ),
        idempotency_key=require_idempotency_key(),
        request_id=req_id,
        client_version=version,
        expected_kind=PaperworkKind.COUNT_SHEET,
        audit_writer=current_app.config["AUDIT_WRITER"],
    )))


@paperwork_bp.post("/paperwork/count-sheets/<uuid:record_id>/actions")
@require_browser_session
@require_browser_csrf
def action_route(record_id: UUID):
    payload = json_body(exact={"action"}, message="The action request is invalid.")
    action = payload.get("action")
    if not isinstance(action, str) or action not in _ACTIONS:
        raise ApiError("validation_failed", "The action is invalid.", status=400)
    req_id, version = request_metadata()
    return _write(lambda db: record_paperwork_action(
        db,
        current_browser_actor(),
        record_id=record_id,
        action=action,
        idempotency_key=require_idempotency_key(),
        request_id=req_id,
        client_version=version,
        expected_kind=PaperworkKind.COUNT_SHEET,
        audit_writer=current_app.config["AUDIT_WRITER"],
    ))
