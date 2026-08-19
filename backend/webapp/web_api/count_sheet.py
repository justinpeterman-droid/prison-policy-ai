"""Cookie-authenticated, server-calculated NCU Days Count routes."""
from datetime import date
from pathlib import Path
from uuid import UUID

from flask import Blueprint, current_app, g, request
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from backend.identity.idempotency import IdempotencyConflict, RequestInProgress
from backend.paperwork.contracts import PaperworkIdentity, SaveOperationalPaperworkRequest
from backend.paperwork.count_definition import (
    CountDefinitionUnavailable,
    LoadedCountSheetDefinition,
    build_count_paperwork_content,
    load_count_sheet_definition,
)
from backend.paperwork.counts import CountCellInvalid
from backend.paperwork.service import (
    OperationalPaperworkView,
    PaperworkIdentityConflict,
    PaperworkNotFound,
    PaperworkRevisionConflict,
    create_operational_paperwork,
    get_operational_paperwork,
    save_operational_paperwork,
)
from backend.persistence.database import DatabaseUnavailable
from backend.persistence.models.paperwork import OperationalPaperworkRecord
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.responses import success
from backend.webapp.web_api.middleware import (
    current_browser_actor,
    current_browser_session,
    require_browser_csrf,
    require_browser_session,
)


count_sheet_bp = Blueprint("web_count_sheet", __name__)


def _validation_error() -> ApiError:
    return ApiError(
        "validation_failed",
        "The Count Sheet request is invalid.",
        status=400,
    )


def _definition() -> LoadedCountSheetDefinition:
    configured = current_app.config.get("NCU_COUNT_DEFINITION_PATH")
    path = Path(configured) if isinstance(configured, (str, Path)) else None
    try:
        return load_count_sheet_definition(path) if path is not None else load_count_sheet_definition()
    except CountDefinitionUnavailable:
        raise ApiError(
            "count_definition_unavailable",
            "The approved NCU Days Count template has not been published.",
            status=503,
            retryable=False,
        ) from None


def _definition_data(loaded: LoadedCountSheetDefinition) -> dict[str, object]:
    definition = loaded.definition
    return {
        "schema_version": definition.schema_version,
        "title": definition.title,
        "definition_sha256": loaded.sha256,
        "rows": [
            {"id": row.id, "label": row.label, "section": row.section}
            for row in definition.rows
        ],
        "columns": [
            {"id": column.id, "label": column.label}
            for column in definition.columns
        ],
        "operational_total_column": definition.operational_total_column,
    }


def _view_data(view: OperationalPaperworkView) -> dict[str, object]:
    row = view.record
    return {
        "record_id": str(row.id),
        "record_date": row.record_date.isoformat(),
        "shift": row.shift,
        "record_key": row.record_key,
        "current_revision_number": view.revision_number,
        "content": view.content,
        "created_at": row.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": view.updated_at.isoformat().replace("+00:00", "Z"),
    }


def _body(exact: set[str]) -> dict:
    value = request.get_json(silent=True)
    if not isinstance(value, dict) or set(value) != exact:
        raise _validation_error()
    return value


def _expected(value: object) -> int:
    if type(value) is not int or not 0 <= value <= 99_999:
        raise _validation_error()
    return value


def _idempotency_key() -> str:
    value = request.headers.get("Idempotency-Key", "")
    if not value or len(value) > 128:
        raise _validation_error()
    return value


def _metadata() -> tuple[str, str]:
    return str(g.request_id), str(g.client_version or "0.0.0")


def _identity(raw_date: object, raw_shift: object) -> PaperworkIdentity:
    try:
        parsed_date = date.fromisoformat(raw_date) if isinstance(raw_date, str) else raw_date
        return PaperworkIdentity(
            paperwork_type="ncu_days_count",
            record_date=parsed_date,
            shift=raw_shift,
            record_key="primary",
        )
    except (TypeError, ValueError, ValidationError):
        raise _validation_error() from None


def _if_match(base_revision_number: int) -> None:
    supplied = request.headers.get("If-Match")
    if supplied is not None and supplied != f'"{base_revision_number}"':
        raise _validation_error()


def _constraint_name(error: IntegrityError) -> str | None:
    diagnostic = getattr(getattr(error, "orig", None), "diag", None)
    return getattr(diagnostic, "constraint_name", None)


def _write(operation, *, created: bool = False):
    db = current_browser_session()
    try:
        view = operation(db)
        db.commit()
        return success(_view_data(view), status=201 if created else 200)
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
            "The Count Sheet changed; reload before saving.",
            status=409,
            details={"current_revision_number": error.current_revision_number},
        ) from None
    except PaperworkIdentityConflict:
        db.rollback()
        raise ApiError(
            "paperwork_identity_conflict",
            "A Count Sheet already exists for this date and shift.",
            status=409,
        ) from None
    except PaperworkNotFound:
        db.rollback()
        raise ApiError("not_found", "Count Sheet not found.", status=404) from None
    except (CountCellInvalid, ValidationError, ValueError, TypeError):
        db.rollback()
        raise _validation_error() from None
    except IntegrityError as error:
        db.rollback()
        if _constraint_name(error) == "uq_operational_paperwork_identity":
            raise ApiError(
                "paperwork_identity_conflict",
                "A Count Sheet already exists for this date and shift.",
                status=409,
            ) from None
        raise ApiError(
            "revision_conflict",
            "The Count Sheet changed; reload before saving.",
            status=409,
        ) from None
    except OperationalError as error:
        db.rollback()
        sqlstate = getattr(getattr(error, "orig", None), "sqlstate", None)
        if sqlstate in {"40P01", "40001", "55P03"}:
            raise ApiError(
                "revision_conflict",
                "The Count Sheet changed; reload before saving.",
                status=409,
            ) from None
        raise ApiError(
            "dependency_unavailable",
            "The Count Sheet is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db.rollback()
        raise ApiError(
            "dependency_unavailable",
            "The Count Sheet is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@count_sheet_bp.get("/count-sheet/definition", endpoint="definition")
@require_browser_session
def definition_route():
    return success(_definition_data(_definition()))


@count_sheet_bp.get("/count-sheet", endpoint="lookup")
@require_browser_session
def lookup_route():
    if set(request.args) != {"date", "shift"}:
        raise _validation_error()
    identity = _identity(request.args.get("date"), request.args.get("shift"))
    db = current_browser_session()
    try:
        record_id = db.scalar(select(OperationalPaperworkRecord.id).where(
            OperationalPaperworkRecord.paperwork_type == identity.paperwork_type,
            OperationalPaperworkRecord.record_date == identity.record_date,
            OperationalPaperworkRecord.shift == identity.shift,
            OperationalPaperworkRecord.record_key == identity.record_key,
            OperationalPaperworkRecord.archived_at.is_(None),
        ))
        if record_id is None:
            return success({"item": None})
        return success({"item": _view_data(get_operational_paperwork(
            db,
            current_browser_actor(),
            record_id=record_id,
        ))})
    except PaperworkNotFound:
        return success({"item": None})
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "The Count Sheet is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@count_sheet_bp.post("/count-sheet", endpoint="create")
@require_browser_session
@require_browser_csrf
def create_route():
    payload = _body({"record_date", "shift", "values", "expected_operational_total"})
    loaded = _definition()
    content = build_count_paperwork_content(
        loaded,
        values=payload["values"],
        expected_operational_total=_expected(payload["expected_operational_total"]),
    )
    identity = _identity(payload["record_date"], payload["shift"])
    request_id, client_version = _metadata()
    return _write(
        lambda db: create_operational_paperwork(
            db,
            current_browser_actor(),
            identity=identity,
            content=content,
            idempotency_key=_idempotency_key(),
            request_id=request_id,
            client_version=client_version,
            audit_writer=current_app.config["AUDIT_WRITER"],
        ),
        created=True,
    )


@count_sheet_bp.patch("/count-sheet/<uuid:record_id>", endpoint="save")
@require_browser_session
@require_browser_csrf
def save_route(record_id: UUID):
    payload = _body({
        "values",
        "expected_operational_total",
        "base_revision_number",
        "reason",
    })
    base = payload["base_revision_number"]
    reason = payload["reason"]
    if type(base) is not int or base < 1 or reason not in {"autosave", "manual_save"}:
        raise _validation_error()
    _if_match(base)
    content = build_count_paperwork_content(
        _definition(),
        values=payload["values"],
        expected_operational_total=_expected(payload["expected_operational_total"]),
    )
    request_id, client_version = _metadata()
    model = SaveOperationalPaperworkRequest(
        content=content,
        base_revision_number=base,
        reason=reason,
    )
    return _write(lambda db: save_operational_paperwork(
        db,
        current_browser_actor(),
        record_id=record_id,
        request_model=model,
        idempotency_key=_idempotency_key(),
        request_id=request_id,
        client_version=client_version,
        audit_writer=current_app.config["AUDIT_WRITER"],
    ))
