"""Authorized employee report queues, content, history, restore, and recovery."""
from datetime import UTC, date, datetime
import json
from uuid import UUID

from flask import Blueprint, current_app, g, request
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from backend.identity.idempotency import IdempotencyConflict, RequestInProgress
from backend.persistence.database import DatabaseUnavailable
from backend.persistence.models.identity import StaffMember
from backend.reports.persistence import (
    ReportNotFound,
    ReportRevisionNotFound,
    ReportView,
    create_report_recovery_record,
    get_report,
    get_report_revision,
    list_report_revisions,
    list_reports,
    report_revision_content,
    restore_report_record,
    save_report_record,
    save_report_status_record,
)
from backend.reports.revisions import RevisionConflict, RevisionTargetMissing
from backend.webapp.api_v1.client_policy import require_compatible_write
from backend.webapp.api_v1.context import request_id
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.middleware import (
    current_actor,
    current_request_session,
    require_access_token,
)
from backend.webapp.api_v1.pagination import InvalidCursor, decode_cursor, encode_cursor
from backend.webapp.api_v1.responses import success
from backend.webapp.api_v1.schemas.reporting import ReportContentV1, SaveReportRequest


reports_bp = Blueprint("reports_api", __name__)
LIST_FIELDS = {
    "relationship", "status", "incident_date_from", "incident_date_to", "category",
    "updated_at_from", "updated_at_to", "limit", "cursor",
}
SAVE_FIELDS = {"content", "base_revision_number", "reason"}
STATUS_FIELDS = {"status", "base_revision_number"}
STATUSES = {"in_progress", "completed", "archived"}


def _timestamp(value) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _body(*, exact: set[str] | None = None, allowed: set[str] | None = None) -> dict:
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise ApiError("validation_failed", "The report request is invalid.", status=400)
    keys = set(value)
    if (exact is not None and keys != exact) or (
        allowed is not None and (not keys or not keys <= allowed)
    ):
        raise ApiError("validation_failed", "The report request is invalid.", status=400)
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


def _page_size(raw: str | None) -> int:
    if raw is None:
        return 25
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError("page size is invalid") from None
    if str(value) != raw.strip() or not 1 <= value <= 50:
        raise ValueError("page size is invalid")
    return value


def _date(value: str | None):
    if value is None:
        return None
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("date filter is invalid") from None
    if parsed.isoformat() != value:
        raise ValueError("date filter is invalid")
    return parsed


def _datetime(value: str | None):
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        raise ValueError("updated filter is invalid") from None
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError("updated filter is invalid")
    return parsed


def _staff_data(staff_id: UUID) -> tuple[str, str]:
    staff = current_request_session().get(StaffMember, staff_id)
    if staff is None:
        raise RuntimeError("report staff is unavailable")
    return str(staff.id), " ".join(
        part for part in (staff.rank, staff.first_name, staff.last_name) if part
    )


def _view_data(view: ReportView) -> dict[str, object]:
    row = view.report
    owner_id, owner_name = _staff_data(row.reporting_staff_member_id)
    preparer_id, preparer_name = _staff_data(row.prepared_by_staff_member_id)
    return {
        "report_id": str(row.id),
        "incident_id": str(row.incident_id),
        "report_type": getattr(row.report_type, "value", row.report_type),
        "status": view.status,
        "current_revision_number": view.revision_number,
        "content": view.content,
        "reporting_staff_member_id": owner_id,
        "reporting_officer_display_name": owner_name,
        "prepared_by_staff_member_id": preparer_id,
        "preparer_display_name": preparer_name,
        "last_editor_staff_member_id": str(view.editor_staff_member_id),
        "last_editor_display_name": view.editor_display_name,
        "created_at": _timestamp(row.created_at),
        "updated_at": _timestamp(view.updated_at),
    }


def _summary_data(item) -> dict[str, object]:
    report = item.report
    incident = item.incident
    return {
        "report_id": str(report.id),
        "incident_id": str(report.incident_id),
        "report_type": getattr(report.report_type, "value", report.report_type),
        "relationship": item.relationship,
        "reporting_staff_member_id": str(report.reporting_staff_member_id),
        "reporting_officer_display_name": item.reporting_officer_display_name,
        "prepared_by_staff_member_id": str(report.prepared_by_staff_member_id),
        "preparer_display_name": item.preparer_display_name,
        "category": incident.category,
        "incident_date": incident.incident_date.isoformat() if incident.incident_date else None,
        "status": report.status,
        "updated_at": _timestamp(report.updated_at),
        "current_revision_number": report.current_revision_number,
    }


def _source_revision_number(row) -> int | None:
    value = (row.provenance or {}).get("source_revision_number")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _revision_summary(row, current_revision_number: int) -> dict[str, object]:
    editor_id, editor_name = _staff_data(row.editor_staff_member_id)
    return {
        "revision_id": str(row.id),
        "revision_number": row.revision_number,
        "reason": row.reason,
        "changed_fields": list((row.changed_fields or {}).get("fields", [])),
        "editor_staff_member_id": editor_id,
        "editor_display_name": editor_name,
        "client_version": row.client_version,
        "created_at": _timestamp(row.created_at),
        "source_revision_number": _source_revision_number(row),
        "is_current": row.revision_number == current_revision_number,
    }


def _handle_write(operation, *, recovery: bool = False):
    db = current_request_session()
    try:
        result, status = operation(db)
        if recovery:
            view, recovery_number = result
            data = {
                "report_id": str(view.report.id),
                "recovery_revision_number": recovery_number,
                "current_revision_number": view.revision_number,
                "status": view.status,
                "content": view.content,
                "editor_staff_member_id": str(view.editor_staff_member_id),
                "editor_display_name": view.editor_display_name,
                "created_at": _timestamp(view.updated_at),
            }
        else:
            data = _view_data(result)
        db.commit()
        return success(data, status=status)
    except RequestInProgress as error:
        db.rollback()
        raise ApiError("request_in_progress", str(error), status=409, retryable=True) from None
    except IdempotencyConflict as error:
        db.rollback()
        raise ApiError("idempotency_conflict", str(error), status=409) from None
    except RevisionConflict as error:
        db.rollback()
        raise ApiError(
            "revision_conflict", "The report changed; reload before saving.", status=409,
            details={
                "current_revision_number": error.current_revision_number,
                "current_editor_display_name": error.current_editor_display_name,
                "current_edited_at": _timestamp(error.updated_at),
                "changed_fields": list(error.changed_fields),
            },
        ) from None
    except (ReportNotFound, ReportRevisionNotFound, RevisionTargetMissing):
        db.rollback()
        raise ApiError("not_found", "Report not found.", status=404) from None
    except (ValidationError, ValueError, TypeError):
        db.rollback()
        raise ApiError("validation_failed", "The report request is invalid.", status=400) from None
    except IntegrityError:
        db.rollback()
        raise ApiError(
            "revision_conflict", "The report changed; reload before saving.", status=409,
        ) from None
    except OperationalError as error:
        db.rollback()
        sqlstate = getattr(getattr(error, "orig", None), "sqlstate", None)
        if sqlstate in {"40P01", "40001", "55P03"}:
            raise ApiError(
                "revision_conflict", "The report changed; reload before saving.", status=409,
            ) from None
        raise ApiError(
            "dependency_unavailable", "Report storage is temporarily unavailable.",
            status=503, retryable=True,
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db.rollback()
        raise ApiError(
            "dependency_unavailable", "Report storage is temporarily unavailable.",
            status=503, retryable=True,
        ) from None


@reports_bp.get("", endpoint="list")
@require_access_token
def list_route():
    try:
        if not set(request.args) <= LIST_FIELDS:
            raise ValueError("report filters are invalid")
        relationship = request.args.get("relationship")
        if relationship not in {"owned", "prepared"}:
            raise ValueError("relationship is invalid")
        status = request.args.get("status")
        if status is not None and status not in STATUSES:
            raise ValueError("status filter is invalid")
        category = request.args.get("category")
        if category is not None and (not category or len(category) > 120):
            raise ValueError("category filter is invalid")
        key = current_app.config["IDENTITY_SETTINGS"].cursor_signing_key
        if not key:
            raise RuntimeError("report pagination key is unavailable")
        raw_cursor = request.args.get("cursor")
        cursor = decode_cursor(raw_cursor, key) if raw_cursor else None
        incident_date_from = _date(request.args.get("incident_date_from"))
        incident_date_to = _date(request.args.get("incident_date_to"))
        updated_at_from = _datetime(request.args.get("updated_at_from"))
        updated_at_to = _datetime(request.args.get("updated_at_to"))
        if (
            incident_date_from is not None and incident_date_to is not None
            and incident_date_from > incident_date_to
        ) or (
            updated_at_from is not None and updated_at_to is not None
            and updated_at_from > updated_at_to
        ):
            raise ValueError("report filter range is invalid")
        page = list_reports(
            current_request_session(), current_actor(), relationship=relationship,
            limit=_page_size(request.args.get("limit")), cursor=cursor, status=status,
            incident_date_from=incident_date_from,
            incident_date_to=incident_date_to,
            category=category,
            updated_at_from=updated_at_from,
            updated_at_to=updated_at_to,
        )
        return success({
            "items": [_summary_data(item) for item in page.items],
            "next_cursor": encode_cursor(page.next_cursor, key) if page.next_cursor else None,
        })
    except (InvalidCursor, ValueError):
        raise ApiError("validation_failed", "Report pagination is invalid.", status=400) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable", "Report storage is temporarily unavailable.",
            status=503, retryable=True,
        ) from None


@reports_bp.get("/<uuid:report_id>", endpoint="get")
@require_access_token
def get_route(report_id: UUID):
    try:
        return success(_view_data(get_report(
            current_request_session(), current_actor(), report_id)))
    except ReportNotFound:
        raise ApiError("not_found", "Report not found.", status=404) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable", "Report storage is temporarily unavailable.",
            status=503, retryable=True,
        ) from None


@reports_bp.patch("/<uuid:report_id>", endpoint="save")
@require_access_token
@require_compatible_write
def save_route(report_id: UUID):
    payload = _body(allowed=SAVE_FIELDS | STATUS_FIELDS)
    req_id, version = _metadata()
    if set(payload) == STATUS_FIELDS:
        base = payload.get("base_revision_number")
        if not isinstance(base, int) or isinstance(base, bool) or base < 0:
            raise ApiError("validation_failed", "The report request is invalid.", status=400)
        if payload.get("status") not in STATUSES:
            raise ApiError("validation_failed", "The report request is invalid.", status=400)
        _validate_if_match(base)
        return _handle_write(lambda db: (
            save_report_status_record(
                db, current_actor(), report_id, payload["status"], base,
                request.headers.get("Idempotency-Key", ""), request_id=req_id,
                client_version=version, audit_writer=current_app.config["AUDIT_WRITER"],
            ),
            200,
        ))
    if "content" not in payload or "base_revision_number" not in payload:
        raise ApiError("validation_failed", "The report request is invalid.", status=400)
    try:
        model = SaveReportRequest.model_validate_json(json.dumps(payload))
    except ValidationError:
        raise ApiError("validation_failed", "The report request is invalid.", status=400) from None
    _validate_if_match(model.base_revision_number)
    return _handle_write(lambda db: (
        save_report_record(
            db, current_actor(), report_id, model,
            request.headers.get("Idempotency-Key", ""), request_id=req_id,
            client_version=version, audit_writer=current_app.config["AUDIT_WRITER"],
        ),
        200,
    ))


@reports_bp.get("/<uuid:report_id>/revisions", endpoint="revision_list")
@require_access_token
def revision_list_route(report_id: UUID):
    db = current_request_session()
    try:
        # Authorization intentionally precedes cursor parsing, so an unrelated
        # caller cannot use validation differences to infer report existence.
        current = get_report(db, current_actor(), report_id)
        key = current_app.config["IDENTITY_SETTINGS"].cursor_signing_key
        if not key:
            raise RuntimeError("report revision pagination key is unavailable")
        raw_cursor = request.args.get("cursor")
        cursor = decode_cursor(raw_cursor, key) if raw_cursor else None
        if not set(request.args) <= {"limit", "cursor"}:
            raise ValueError("revision pagination is invalid")
        page = list_report_revisions(
            db, current_actor(), report_id,
            limit=_page_size(request.args.get("limit")), cursor=cursor,
        )
        return success({
            "items": [
                _revision_summary(row, current.revision_number) for row in page.items
            ],
            "next_cursor": encode_cursor(page.next_cursor, key) if page.next_cursor else None,
        })
    except ReportNotFound:
        raise ApiError("not_found", "Report not found.", status=404) from None
    except (InvalidCursor, ValueError):
        raise ApiError("validation_failed", "Revision pagination is invalid.", status=400) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable", "Report storage is temporarily unavailable.",
            status=503, retryable=True,
        ) from None


@reports_bp.get(
    "/<uuid:report_id>/revisions/<int:revision_number>", endpoint="revision_detail",
)
@require_access_token
def revision_detail_route(report_id: UUID, revision_number: int):
    try:
        db = current_request_session()
        current = get_report(db, current_actor(), report_id)
        row = get_report_revision(db, current_actor(), report_id, revision_number)
        return success({
            **_revision_summary(row, current.revision_number),
            "content": report_revision_content(row),
        })
    except (ReportNotFound, ReportRevisionNotFound):
        raise ApiError("not_found", "Report not found.", status=404) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable", "Report storage is temporarily unavailable.",
            status=503, retryable=True,
        ) from None


@reports_bp.post("/<uuid:report_id>/restore", endpoint="restore")
@require_access_token
@require_compatible_write
def restore_route(report_id: UUID):
    payload = _body(exact={"revision_number"})
    req_id, version = _metadata()
    return _handle_write(lambda db: (
        restore_report_record(
            db, current_actor(), report_id, payload["revision_number"],
            request.headers.get("Idempotency-Key", ""), request_id=req_id,
            client_version=version, audit_writer=current_app.config["AUDIT_WRITER"],
        ),
        200,
    ))


@reports_bp.post("/<uuid:report_id>/recovery-revisions", endpoint="recovery")
@require_access_token
@require_compatible_write
def recovery_route(report_id: UUID):
    payload = _body(exact={"content", "base_revision_number"})
    try:
        content = ReportContentV1.model_validate_json(json.dumps(payload["content"]))
        base = payload["base_revision_number"]
        if not isinstance(base, int) or isinstance(base, bool) or base < 0:
            raise ValueError
    except (ValidationError, ValueError, TypeError):
        raise ApiError("validation_failed", "The report request is invalid.", status=400) from None
    _validate_if_match(base)
    req_id, version = _metadata()
    return _handle_write(lambda db: (
        create_report_recovery_record(
            db, current_actor(), report_id, content, base,
            request.headers.get("Idempotency-Key", ""), request_id=req_id,
            client_version=version, audit_writer=current_app.config["AUDIT_WRITER"],
        ),
        201,
    ), recovery=True)
