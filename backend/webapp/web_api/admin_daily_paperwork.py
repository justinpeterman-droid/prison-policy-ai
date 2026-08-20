"""Elevated administrator lifecycle routes for daily operational paperwork."""

from __future__ import annotations

from datetime import UTC, date, datetime
import json
from uuid import UUID

from flask import Blueprint, current_app, request
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from backend.identity.browser_admin import require_browser_admin_elevation
from backend.identity.elevation import AdminElevationRequired
from backend.identity.idempotency import IdempotencyConflict, RequestInProgress
from backend.paperwork.actions import record_paperwork_action
from backend.paperwork.daily import (
    AssignmentRosterV1,
    DetectorSignOutV1,
    MetalDetectorTestV1,
    PerimeterCheckV1,
    RandomSearchLogV1,
    UniformInspectionV1,
    build_uniform_rows_from_roster,
    calculate_roster_coverage,
    validate_daily_payload,
)
from backend.paperwork.daily_templates import DailyPaperworkKind, load_daily_template
from backend.paperwork.models import PaperworkKind, PaperworkView
from backend.paperwork.schemas import SavePaperworkRequest
from backend.paperwork.service import (
    PaperworkAlreadyExists,
    PaperworkNotFound,
    PaperworkRevisionConflict,
    PaperworkRevisionNotFound,
    copy_previous_daily_record,
    get_paperwork_record,
    list_paperwork_records,
    list_paperwork_revisions,
    restore_paperwork_record,
    save_paperwork_record,
)
from backend.persistence.database import DatabaseUnavailable
from backend.webapp.api_v1.errors import ApiError
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
    require_browser_role,
    require_browser_session,
)


admin_daily_paperwork_bp = Blueprint("web_admin_daily_paperwork", __name__)
_SAVE_FIELDS = {
    "schema_version",
    "work_date",
    "shift",
    "payload",
    "base_revision_number",
    "reason",
}
_ACTIONS = {"preview", "print", "download_pdf"}
_INSPECTION_COLUMNS = ("shirt", "pants", "shoes", "cap", "coat", "id", "hair", "nails")


def _kind(value: str) -> DailyPaperworkKind:
    try:
        return DailyPaperworkKind(value)
    except ValueError:
        raise ApiError(
            "validation_failed", "The daily paperwork kind is invalid.", status=400,
        ) from None


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


def _validation_fields(error: ValidationError) -> list[str]:
    return sorted({
        ".".join(str(part) for part in item.get("loc", ()))[:120]
        for item in error.errors(include_input=False, include_url=False)
        if item.get("loc")
    })[:20]


def _parse_date(value: object, *, field: str) -> date:
    if not isinstance(value, str):
        raise ApiError("validation_failed", f"{field} is invalid.", status=400)
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ApiError("validation_failed", f"{field} is invalid.", status=400) from None
    if parsed.isoformat() != value:
        raise ApiError("validation_failed", f"{field} is invalid.", status=400)
    return parsed


def _parse_shift(value: object) -> str:
    if not isinstance(value, str):
        raise ApiError("validation_failed", "shift is invalid.", status=400)
    cleaned = " ".join(value.split())
    if not cleaned or len(cleaned) > 32:
        raise ApiError("validation_failed", "shift is invalid.", status=400)
    return cleaned


def _daily_validation(view: PaperworkView) -> tuple[dict[str, object], int]:
    model = validate_daily_payload(view.kind.value, view.payload)
    if isinstance(model, AssignmentRosterV1):
        warnings = [
            {
                "code": warning.code,
                "message": warning.message,
                "zone_code": warning.zone_code,
                "post_code": warning.post_code,
                "staff_id": str(warning.staff_id) if warning.staff_id else None,
            }
            for warning in calculate_roster_coverage(model)
        ]
        return {"coverage_warnings": warnings}, len(warnings)
    if isinstance(model, UniformInspectionV1):
        unsatisfactory = sum(
            getattr(row, column) == "U"
            for row in model.rows
            for column in _INSPECTION_COLUMNS
        )
        missing_comments = sum(
            any(getattr(row, column) == "U" for column in _INSPECTION_COLUMNS)
            and not row.comments.strip()
            for row in model.rows
        )
        return {
            "unsatisfactory_count": unsatisfactory,
            "missing_comment_count": missing_comments,
        }, missing_comments
    if isinstance(model, MetalDetectorTestV1):
        failed = sum(
            test.result == "F"
            for detector in model.detectors
            for test in detector.tests
        )
        return {"failed_test_count": failed}, failed
    if isinstance(model, PerimeterCheckV1):
        incomplete = sum(check.result is None for check in model.checks)
        unsatisfactory = sum(check.result == "U" for check in model.checks)
        return {
            "incomplete_count": incomplete,
            "unsatisfactory_count": unsatisfactory,
        }, unsatisfactory
    if isinstance(model, RandomSearchLogV1):
        incomplete = sum(
            block.officer is None
            or block.search_date is None
            or block.search_time is None
            for section in model.sections
            for block in section.blocks
        )
        return {"incomplete_count": incomplete}, 0
    if isinstance(model, DetectorSignOutV1):
        incomplete = sum(
            row.staff is None or not row.area_of_assignment.strip()
            for row in model.units
        )
        return {"incomplete_count": incomplete}, 0
    raise RuntimeError("daily paperwork payload type is unsupported")


def daily_record_data(
    view: PaperworkView,
    *,
    include_payload: bool = True,
) -> dict[str, object]:
    """Serialize one daily record without placing content in summary metadata."""
    definition = load_daily_template(view.kind.value)
    validation, warning_count = _daily_validation(view)
    data: dict[str, object] = {
        "record_id": str(view.record_id),
        "kind": view.kind.value,
        "title": definition.title,
        "work_date": view.work_date.isoformat(),
        "shift": view.shift,
        "revision": view.current_revision_number,
        "current_revision_number": view.current_revision_number,
        "state": "needs_attention" if warning_count else "saved",
        "warning_count": warning_count,
        "validation": validation,
        "created_by_staff_member_id": str(view.created_by_staff_member_id),
        "last_editor_staff_member_id": str(view.last_editor_staff_member_id),
        "created_at": timestamp(view.created_at),
        "updated_at": timestamp(view.updated_at),
    }
    if include_payload:
        data["payload"] = view.payload
        data["template"] = {
            "schema_version": definition.schema_version,
            "title": definition.title,
            "print_orientation": definition.print_orientation,
            "definition": definition.definition,
        }
    return data


def daily_template_data(kind: DailyPaperworkKind | str) -> dict[str, object]:
    """Serialize one immutable sanitized definition for an editor start state."""
    selected_kind = kind if isinstance(kind, DailyPaperworkKind) else DailyPaperworkKind(kind)
    definition = load_daily_template(selected_kind)
    return {
        "kind": selected_kind.value,
        "schema_version": definition.schema_version,
        "title": definition.title,
        "print_orientation": definition.print_orientation,
        "definition": definition.definition,
    }


def _revision_data(row) -> dict[str, object]:
    return {
        "revision_number": row.revision_number,
        "reason": row.reason,
        "changed_fields": list((row.changed_fields or {}).get("paths", [])),
        "editor_staff_member_id": str(row.editor_staff_member_id),
        "client_version": row.client_version,
        "created_at": timestamp(row.created_at),
    }


def _save_model(kind: DailyPaperworkKind) -> SavePaperworkRequest:
    payload = json_body(exact=_SAVE_FIELDS, message="The daily paperwork request is invalid.")
    try:
        model = SavePaperworkRequest.model_validate_json(
            json.dumps(payload, ensure_ascii=False, allow_nan=False)
        )
        daily = validate_daily_payload(kind, model.payload)
    except ValidationError as error:
        raise ApiError(
            "validation_failed",
            "The daily paperwork request is invalid.",
            status=400,
            details={"fields": _validation_fields(error)},
        ) from None
    except (TypeError, ValueError):
        raise ApiError(
            "validation_failed", "The daily paperwork request is invalid.", status=400,
        ) from None
    if model.shift is None or daily.work_date != model.work_date or daily.shift != model.shift:
        raise ApiError(
            "validation_failed",
            "The payload date and shift must match the record date and shift.",
            status=400,
        )
    return model.model_copy(update={"payload": daily.model_dump(mode="json")})


def _record_for_kind(kind: DailyPaperworkKind, record_id: UUID) -> PaperworkView:
    view = get_paperwork_record(
        current_browser_session(), current_browser_actor(), record_id,
    )
    if view.kind.value != kind.value:
        raise PaperworkNotFound("Paperwork record not found.")
    return view


def _write(operation, *, created: bool = False):
    db = current_browser_session()
    try:
        value = operation(db)
        db.commit()
        return success(value, status=201 if created else 200)
    except RequestInProgress as error:
        db.rollback()
        raise ApiError("request_in_progress", str(error), status=409, retryable=True) from None
    except IdempotencyConflict as error:
        db.rollback()
        raise ApiError("idempotency_conflict", str(error), status=409) from None
    except PaperworkRevisionConflict as error:
        db.rollback()
        raise ApiError(
            "revision_conflict",
            "The daily record changed. Your local values have been preserved; reload before saving again.",
            status=409,
            details={"current_revision_number": error.current_revision_number},
        ) from None
    except PaperworkAlreadyExists as error:
        db.rollback()
        raise ApiError(
            "record_already_exists",
            "A record already exists for this date and shift; open the saved record.",
            status=409,
            details={"record_id": str(error.record_id)},
        ) from None
    except (PaperworkNotFound, PaperworkRevisionNotFound):
        db.rollback()
        raise ApiError("not_found", "Daily paperwork not found.", status=404) from None
    except ValidationError as error:
        db.rollback()
        raise ApiError(
            "validation_failed",
            "The daily paperwork request is invalid.",
            status=400,
            details={"fields": _validation_fields(error)},
        ) from None
    except (TypeError, ValueError):
        db.rollback()
        raise ApiError(
            "validation_failed", "The daily paperwork request is invalid.", status=400,
        ) from None
    except IntegrityError:
        db.rollback()
        raise ApiError(
            "revision_conflict",
            "The daily record changed; reload before saving again.",
            status=409,
        ) from None
    except OperationalError as error:
        db.rollback()
        state = getattr(getattr(error, "orig", None), "sqlstate", None)
        if state in LOCK_CONFLICT_STATES:
            raise ApiError(
                "revision_conflict", "The daily record changed; reload before saving again.", status=409,
            ) from None
        raise ApiError(
            "dependency_unavailable",
            "Daily paperwork storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db.rollback()
        raise ApiError(
            "dependency_unavailable",
            "Daily paperwork storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@admin_daily_paperwork_bp.get("/paperwork/daily")
@require_browser_session
@require_browser_role("admin")
def list_daily_route():
    if set(request.args) - {"work_date", "shift", "kind"}:
        raise ApiError("validation_failed", "The daily paperwork request is invalid.", status=400)
    _require_elevation()
    work_date_raw = request.args.get("work_date")
    shift_raw = request.args.get("shift")
    kind_raw = request.args.get("kind")
    selected_date = _parse_date(work_date_raw, field="work_date") if work_date_raw else None
    selected_shift = _parse_shift(shift_raw) if shift_raw else None
    selected_kind = _kind(kind_raw) if kind_raw else None
    try:
        page = list_paperwork_records(
            current_browser_session(),
            current_browser_actor(),
            kind=selected_kind.value if selected_kind else None,
            work_date=selected_date,
            shift=selected_shift,
            limit=50,
        )
        items = [
            daily_record_data(item, include_payload=False)
            for item in page.items
            if item.kind is not PaperworkKind.COUNT_SHEET
        ]
        return success({"items": items, "next_cursor": None})
    except (ValidationError, ValueError):
        raise ApiError("validation_failed", "The daily paperwork request is invalid.", status=400) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable", "Daily paperwork storage is temporarily unavailable.", status=503, retryable=True,
        ) from None


@admin_daily_paperwork_bp.post("/paperwork/daily/<kind>")
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def create_daily_route(kind: str):
    _require_elevation()
    selected_kind = _kind(kind)
    model = _save_model(selected_kind)
    if model.base_revision_number is not None:
        raise ApiError("validation_failed", "A new record cannot include a base revision.", status=400)
    req_id, version = request_metadata()
    return _write(lambda db: daily_record_data(save_paperwork_record(
        db,
        current_browser_actor(),
        kind=selected_kind.value,
        request_model=model,
        idempotency_key=require_idempotency_key(),
        request_id=req_id,
        client_version=version,
        audit_writer=current_app.config["AUDIT_WRITER"],
    )), created=True)


@admin_daily_paperwork_bp.get("/paperwork/daily/<kind>/template")
@require_browser_session
@require_browser_role("admin")
def get_daily_template_route(kind: str):
    if request.args:
        raise ApiError("validation_failed", "The daily template request is invalid.", status=400)
    _require_elevation()
    return success(daily_template_data(_kind(kind)))


@admin_daily_paperwork_bp.get("/paperwork/daily/<kind>/<uuid:record_id>")
@require_browser_session
@require_browser_role("admin")
def get_daily_route(kind: str, record_id: UUID):
    _require_elevation()
    selected_kind = _kind(kind)
    try:
        return success(daily_record_data(_record_for_kind(selected_kind, record_id)))
    except PaperworkNotFound:
        raise ApiError("not_found", "Daily paperwork not found.", status=404) from None
    except (ValidationError, ValueError, DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable", "The saved daily paperwork is unavailable.", status=503, retryable=True,
        ) from None


@admin_daily_paperwork_bp.patch("/paperwork/daily/<kind>/<uuid:record_id>")
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def save_daily_route(kind: str, record_id: UUID):
    _require_elevation()
    selected_kind = _kind(kind)
    model = _save_model(selected_kind)
    if model.base_revision_number is None:
        raise ApiError("validation_failed", "An existing record requires a base revision.", status=400)
    validate_if_match(model.base_revision_number)
    req_id, version = request_metadata()
    return _write(lambda db: daily_record_data(save_paperwork_record(
        db,
        current_browser_actor(),
        record_id=record_id,
        kind=selected_kind.value,
        request_model=model,
        idempotency_key=require_idempotency_key(),
        request_id=req_id,
        client_version=version,
        audit_writer=current_app.config["AUDIT_WRITER"],
    )))


@admin_daily_paperwork_bp.get("/paperwork/daily/<kind>/<uuid:record_id>/revisions")
@require_browser_session
@require_browser_role("admin")
def daily_revisions_route(kind: str, record_id: UUID):
    if request.args:
        raise ApiError("validation_failed", "The revision request is invalid.", status=400)
    _require_elevation()
    selected_kind = _kind(kind)
    try:
        _record_for_kind(selected_kind, record_id)
        page = list_paperwork_revisions(
            current_browser_session(), current_browser_actor(), record_id, limit=100,
        )
        return success({
            "items": [_revision_data(item) for item in page.items],
            "next_cursor": None,
        })
    except PaperworkNotFound:
        raise ApiError("not_found", "Daily paperwork not found.", status=404) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable", "Daily paperwork revisions are temporarily unavailable.", status=503, retryable=True,
        ) from None


@admin_daily_paperwork_bp.post("/paperwork/daily/<kind>/<uuid:record_id>/restore")
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def restore_daily_route(kind: str, record_id: UUID):
    _require_elevation()
    selected_kind = _kind(kind)
    payload = json_body(exact={"revision_number"}, message="The restore request is invalid.")
    req_id, version = request_metadata()

    def operation(db):
        _record_for_kind(selected_kind, record_id)
        return daily_record_data(restore_paperwork_record(
            db,
            current_browser_actor(),
            record_id=record_id,
            source_revision_number=positive_int(payload.get("revision_number"), name="revision_number"),
            idempotency_key=require_idempotency_key(),
            request_id=req_id,
            client_version=version,
            audit_writer=current_app.config["AUDIT_WRITER"],
        ))

    return _write(operation)


@admin_daily_paperwork_bp.post("/paperwork/daily/<kind>/copy-previous")
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def copy_previous_route(kind: str):
    _require_elevation()
    selected_kind = _kind(kind)
    payload = json_body(
        allowed={"target_work_date", "shift", "source_record_id"},
        required={"target_work_date", "shift"},
        message="The copy request is invalid.",
    )
    source_record_id = payload.get("source_record_id")
    try:
        parsed_source_id = UUID(source_record_id) if source_record_id is not None else None
    except (TypeError, ValueError):
        raise ApiError("validation_failed", "The copy request is invalid.", status=400) from None
    req_id, version = request_metadata()
    return _write(lambda db: daily_record_data(copy_previous_daily_record(
        db,
        current_browser_actor(),
        kind=selected_kind.value,
        target_work_date=_parse_date(payload.get("target_work_date"), field="target_work_date"),
        shift=_parse_shift(payload.get("shift")),
        source_record_id=parsed_source_id,
        idempotency_key=require_idempotency_key(),
        request_id=req_id,
        client_version=version,
        audit_writer=current_app.config["AUDIT_WRITER"],
    )), created=True)


@admin_daily_paperwork_bp.post(
    "/paperwork/daily/assignment-roster/<uuid:record_id>/uniform-inspection"
)
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def derive_uniform_route(record_id: UUID):
    _require_elevation()
    payload = json_body(
        exact={"target_work_date", "shift"},
        message="The uniform-inspection request is invalid.",
    )
    target_date = _parse_date(payload.get("target_work_date"), field="target_work_date")
    selected_shift = _parse_shift(payload.get("shift"))
    req_id, version = request_metadata()

    def operation(db):
        roster = _record_for_kind(DailyPaperworkKind.ASSIGNMENT_ROSTER, record_id)
        inspection = build_uniform_rows_from_roster(
            roster.payload,
            roster_record_id=roster.record_id,
            roster_revision_number=roster.current_revision_number,
        ).model_copy(update={"work_date": target_date, "shift": selected_shift})
        model = SavePaperworkRequest(
            schema_version=1,
            work_date=target_date,
            shift=selected_shift,
            payload=inspection.model_dump(mode="json"),
            base_revision_number=None,
            reason="manual_save",
        )
        return daily_record_data(save_paperwork_record(
            db,
            current_browser_actor(),
            kind=PaperworkKind.UNIFORM_INSPECTION,
            request_model=model,
            idempotency_key=require_idempotency_key(),
            request_id=req_id,
            client_version=version,
            audit_writer=current_app.config["AUDIT_WRITER"],
        ))

    return _write(operation, created=True)


@admin_daily_paperwork_bp.post("/paperwork/daily/<kind>/<uuid:record_id>/actions")
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def daily_action_route(kind: str, record_id: UUID):
    _require_elevation()
    selected_kind = _kind(kind)
    payload = json_body(exact={"action"}, message="The action request is invalid.")
    action = payload.get("action")
    if not isinstance(action, str) or action not in _ACTIONS:
        raise ApiError("validation_failed", "The action is invalid.", status=400)
    req_id, version = request_metadata()

    def operation(db):
        _record_for_kind(selected_kind, record_id)
        return record_paperwork_action(
            db,
            current_browser_actor(),
            record_id=record_id,
            action=action,
            idempotency_key=require_idempotency_key(),
            request_id=req_id,
            client_version=version,
            audit_writer=current_app.config["AUDIT_WRITER"],
        )

    return _write(operation)
