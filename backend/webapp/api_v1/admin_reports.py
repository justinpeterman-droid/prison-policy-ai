"""Admin report search, detail, history, edit, restore, and transfer routes.

Every route requires an Admin role AND active server-side elevation (ID-07).
A regular User is shown a concealed 404 rather than a 403, so this surface is
not discoverable to someone who cannot use it -- mirroring how the roster and
other Admin-only surfaces already behave in this product. Restore and
transfer additionally require a purpose-scoped, single-use `X-Admin-Step-Up`
token; editing does not, but is still attributed and idempotent. Every
mutation claims and completes its ID-06 idempotency key in the same
transaction as step-up consumption, revision creation, and the audit write.

Persistence and revision logic live in `backend.reports.persistence` and
`backend.reports.revisions` -- this module only parses/validates the wire
shape, drives the shared services, and renders the response.
"""

from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime
from functools import wraps
import hashlib
import hmac
import json
from typing import TypeVar
from uuid import UUID

from flask import Blueprint, current_app, g, request
from pydantic import ValidationError
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from backend.identity.elevation import (
    AdminElevationRequired,
    StepUpRequired,
    consume_step_up,
)
from backend.identity.idempotency import (
    IdempotencyConflict,
    RequestInProgress,
    claim_idempotency,
    complete_idempotency,
    request_digest,
)
from backend.persistence.database import DatabaseUnavailable
from backend.persistence.models.identity import StaffMember
from backend.reports.persistence import (
    ADMIN_REPORT_FILTER_FIELDS,
    ADMIN_REPORT_SEARCH_SORTS,
    AdminReportFilters,
    AdminReportSearchItem,
    ReportNotFound,
    ReportRevisionNotFound,
    ReportView,
    admin_search_reports,
    get_report_admin,
    get_report_revision_admin,
    list_report_revisions_admin,
    report_revision_content,
    restore_report_admin_record,
    save_report_admin_record,
    transfer_report_ownership_record,
)
from backend.reports.export_service import (
    BULK_EXPORT_MAX_DOCUMENTS,
    BULK_EXPORT_MIME_TYPE,
    BULK_REVISION_SELECTION,
    EXPORT_MIME_TYPE,
    ExportFailure,
    bulk_reference,
    decode_bulk_reference,
    export_reports_zip,
    perform_single_export,
    stream_export,
)
from backend.reports.revisions import (
    RevisionConflict,
    RevisionTargetMissing,
    report_revision_editor_snapshot,
)
from backend.webapp.api_v1.client_policy import require_compatible_write
from backend.webapp.api_v1.context import request_id
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.middleware import (
    current_actor,
    current_request_session,
    require_access_token,
    require_admin_elevation,
    require_step_up,
)
from backend.webapp.api_v1.pagination import (
    InvalidCursor,
    decode_cursor,
    encode_cursor,
    parse_page_size,
)
from backend.webapp.api_v1.responses import success
from backend.webapp.api_v1.reports import export_idempotency_key, export_revision_query
from backend.webapp.api_v1.schemas.reporting import SaveReportRequest
from backend.identity.audit import AuditEventInput
from backend.persistence.models.reporting import Report, ReportRevision
from backend.persistence.models.security import IdempotencyRecord


admin_reports_bp = Blueprint("admin_reports_api", __name__)

STATUSES = {"in_progress", "completed", "archived"}
_RANGE_PAIRS = (
    ("incident_date_from", "incident_date_to"),
    ("created_at_from", "created_at_to"),
    ("modified_at_from", "modified_at_to"),
)
ADMIN_SEARCH_QUERY_FIELDS = set(ADMIN_REPORT_FILTER_FIELDS) | {
    "limit",
    "cursor",
    "sort",
}
TRANSFER_REASON_MAX_LENGTH = 500


def _require_admin_hidden(view):
    """Reject a non-Admin caller with a concealed 404, not a 403.

    Admin report routes must not be discoverable to a regular User -- a role
    mismatch here reads exactly like a missing route.
    """

    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_actor().role != "admin":
            raise ApiError("not_found", "Not found.", status=404)
        return view(*args, **kwargs)

    return wrapped


def _admin_get(view):
    @wraps(view)
    def safe(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except ApiError:
            raise
        except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
            raise ApiError(
                "dependency_unavailable",
                "The Admin service is temporarily unavailable.",
                status=503,
                retryable=True,
            ) from None

    return require_access_token(_require_admin_hidden(require_admin_elevation(safe)))


def _timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _body(*, exact: set[str] | None = None, allowed: set[str] | None = None) -> dict:
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise ApiError(
            "validation_failed", "The admin report request is invalid.", status=400
        )
    keys = set(value)
    if (exact is not None and keys != exact) or (
        allowed is not None and (not keys or not keys <= allowed)
    ):
        raise ApiError(
            "validation_failed", "The admin report request is invalid.", status=400
        )
    return value


def _staff_display(session, staff_id: UUID) -> tuple[str, str]:
    staff = session.get(StaffMember, staff_id)
    if staff is None:
        raise RuntimeError("report staff is unavailable")
    return str(staff.id), " ".join(
        part for part in (staff.rank, staff.first_name, staff.last_name) if part
    )


def _view_data(session, view: ReportView) -> dict[str, object]:
    row = view.report
    owner_name: str | None
    if view.reporting_staff_member_id is None:
        owner_id, owner_name = _staff_display(session, row.reporting_staff_member_id)
    else:
        owner_id = str(view.reporting_staff_member_id)
        owner_name = view.reporting_officer_display_name
    preparer_name: str | None
    if view.prepared_by_staff_member_id is None:
        preparer_id, preparer_name = _staff_display(
            session,
            row.prepared_by_staff_member_id,
        )
    else:
        preparer_id = str(view.prepared_by_staff_member_id)
        preparer_name = view.preparer_display_name
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


def _content_hash(snapshot: dict) -> str:
    import hashlib

    encoded = json.dumps(
        snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _source_revision_number(row) -> int | None:
    provenance = row.provenance or {}
    value = (
        provenance.get("source_revision_number")
        if isinstance(provenance, dict)
        else None
    )
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _revision_summary(session, row, current_revision_number: int) -> dict[str, object]:
    del session
    editor_name, editor_rank = report_revision_editor_snapshot(row)
    return {
        "revision_id": str(row.id),
        "revision_number": row.revision_number,
        "reason": row.reason,
        "source_revision_number": _source_revision_number(row),
        "editor_account_id": str(row.editor_account_id),
        "editor_staff_member_id": str(row.editor_staff_member_id),
        "editor_display_name": editor_name,
        "editor_rank": editor_rank,
        "content_hash": _content_hash(row.snapshot),
        "client_version": row.client_version,
        "created_at": _timestamp(row.created_at),
        "is_current": row.revision_number == current_revision_number,
    }


def _search_item_data(item: AdminReportSearchItem) -> dict[str, object]:
    report, incident = item.report, item.incident
    return {
        "report_id": str(report.id),
        "incident_id": str(report.incident_id),
        "report_type": getattr(report.report_type, "value", report.report_type),
        "status": report.status,
        "category": incident.category,
        "facility": incident.facility,
        "location": incident.location,
        "shift": incident.shift,
        "incident_date": incident.incident_date.isoformat()
        if incident.incident_date
        else None,
        "reporting_staff_member_id": str(report.reporting_staff_member_id),
        "prepared_by_staff_member_id": str(report.prepared_by_staff_member_id),
        "last_editor_staff_member_id": str(item.last_editor_staff_member_id),
        "inmate_adc_numbers": list(item.inmate_adc_numbers),
        "current_revision_number": report.current_revision_number,
        "created_at": _timestamp(report.created_at),
        "updated_at": _timestamp(report.updated_at),
    }


def _parse_date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("date filter is invalid") from None
    if parsed.isoformat() != value:
        raise ValueError("date filter is invalid")
    return parsed


def _parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        raise ValueError("timestamp filter is invalid") from None
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError("timestamp filter is invalid")
    return parsed


T = TypeVar("T")


def _optional_filter(
    values: Mapping[str, str], name: str, parser: Callable[[str], T]
) -> T | None:
    raw = values.get(name)
    if raw is None:
        return None
    if raw == "":
        raise ValueError("search filters are invalid")
    return parser(raw)


def _parse_uuid_filter(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise ValueError("search filters are invalid") from None


def _parse_text_filter(value: str) -> str:
    if len(value) > 200:
        raise ValueError("search filters are invalid")
    return value


def _parse_status_filter(value: str) -> str:
    if value not in STATUSES:
        raise ValueError("search filters are invalid")
    return value


def _filters_from_raw(values: Mapping[str, str]) -> AdminReportFilters:
    return AdminReportFilters(
        report_id=_optional_filter(values, "report_id", _parse_uuid_filter),
        incident_id=_optional_filter(values, "incident_id", _parse_uuid_filter),
        reporting_staff_id=_optional_filter(
            values, "reporting_staff_id", _parse_uuid_filter
        ),
        preparer_staff_id=_optional_filter(
            values, "preparer_staff_id", _parse_uuid_filter
        ),
        incident_date_from=_optional_filter(
            values, "incident_date_from", _parse_date
        ),
        incident_date_to=_optional_filter(values, "incident_date_to", _parse_date),
        created_at_from=_optional_filter(
            values, "created_at_from", _parse_datetime
        ),
        created_at_to=_optional_filter(values, "created_at_to", _parse_datetime),
        inmate_first_name=_optional_filter(
            values, "inmate_first_name", _parse_text_filter
        ),
        inmate_middle_name=_optional_filter(
            values, "inmate_middle_name", _parse_text_filter
        ),
        inmate_last_name=_optional_filter(
            values, "inmate_last_name", _parse_text_filter
        ),
        inmate_adc_number=_optional_filter(
            values, "inmate_adc_number", _parse_text_filter
        ),
        category=_optional_filter(values, "category", _parse_text_filter),
        facility=_optional_filter(values, "facility", _parse_text_filter),
        location=_optional_filter(values, "location", _parse_text_filter),
        shift=_optional_filter(values, "shift", _parse_text_filter),
        status=_optional_filter(values, "status", _parse_status_filter),
        last_editor_staff_id=_optional_filter(
            values, "last_editor_staff_id", _parse_uuid_filter
        ),
        modified_at_from=_optional_filter(
            values, "modified_at_from", _parse_datetime
        ),
        modified_at_to=_optional_filter(values, "modified_at_to", _parse_datetime),
    )


def _parse_admin_filters(args) -> AdminReportFilters:
    if not set(args) <= ADMIN_SEARCH_QUERY_FIELDS:
        raise ValueError("search filters are invalid")
    values = {
        name: raw
        for name in ADMIN_REPORT_FILTER_FIELDS
        if (raw := args.get(name)) is not None
    }
    filters = _filters_from_raw(values)
    for lo_name, hi_name in _RANGE_PAIRS:
        lo, hi = getattr(filters, lo_name), getattr(filters, hi_name)
        if lo is not None and hi is not None and lo > hi:
            raise ValueError("search filter range is invalid")
    return filters


def _search_cursor_key(base_key: str, filters: AdminReportFilters, sort: str) -> str:
    context = {
        "sort": sort,
        "filters": {
            name: str(value)
            for name in ADMIN_REPORT_FILTER_FIELDS
            if (value := getattr(filters, name)) is not None
        },
    }
    canonical = json.dumps(
        context,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hmac.new(
        base_key.encode("utf-8"),
        b"admin-report-search\0" + canonical,
        hashlib.sha256,
    ).hexdigest()


def _append_admin_view_audit(session, report_id: UUID) -> None:
    current_app.config["AUDIT_WRITER"].append(
        session,
        AuditEventInput(
            actor_account_id=current_actor().account_id,
            actor_staff_member_id=current_actor().staff_member_id,
            action="report.viewed_by_admin",
            result="success",
            request_id=request_id(),
            target_type="report",
            target_id=report_id,
            details={"report_id": str(report_id)},
            client_version=str(g.client_version),
        ),
    )


@admin_reports_bp.get("", endpoint="search")
@_admin_get
def search_route():
    try:
        filters = _parse_admin_filters(request.args)
        sort = request.args.get("sort", "updated_at_desc")
        if sort not in ADMIN_REPORT_SEARCH_SORTS:
            raise ValueError("sort is invalid")
        base_key = current_app.config["IDENTITY_SETTINGS"].cursor_signing_key
        if not base_key:
            raise RuntimeError("admin report pagination key is unavailable")
        key = _search_cursor_key(base_key, filters, sort)
        raw_cursor = request.args.get("cursor")
        cursor = decode_cursor(raw_cursor, key) if raw_cursor else None
        limit = parse_page_size(request.args.get("limit", "50"))
        db = current_request_session()
        page = admin_search_reports(
            db,
            filters,
            limit=limit,
            cursor=cursor,
            sort=sort,
            actor=current_actor(),
            request_id=request_id(),
            client_version=str(g.client_version),
            audit_writer=current_app.config["AUDIT_WRITER"],
        )
        return success(
            {
                "items": [_search_item_data(item) for item in page.items],
                "next_cursor": encode_cursor(page.next_cursor, key)
                if page.next_cursor
                else None,
            }
        )
    except (InvalidCursor, ValueError):
        raise ApiError(
            "validation_failed", "Search filters are invalid.", status=400
        ) from None


@admin_reports_bp.get("/<uuid:report_id>", endpoint="detail")
@_admin_get
def detail_route(report_id: UUID):
    db = current_request_session()
    try:
        view = get_report_admin(db, report_id)
    except ReportNotFound:
        raise ApiError("not_found", "Report not found.", status=404) from None
    _append_admin_view_audit(db, report_id)
    return success(_view_data(db, view))


@admin_reports_bp.get("/<uuid:report_id>/revisions", endpoint="revision_list")
@_admin_get
def revision_list_route(report_id: UUID):
    db = current_request_session()
    try:
        current = get_report_admin(db, report_id)
        key = current_app.config["IDENTITY_SETTINGS"].cursor_signing_key
        if not key:
            raise RuntimeError("admin report revision pagination key is unavailable")
        raw_cursor = request.args.get("cursor")
        cursor = decode_cursor(raw_cursor, key) if raw_cursor else None
        if not set(request.args) <= {"limit", "cursor"}:
            raise ValueError("revision pagination is invalid")
        page = list_report_revisions_admin(
            db,
            report_id,
            limit=parse_page_size(request.args.get("limit", "50")),
            cursor=cursor,
        )
        return success(
            {
                "items": [
                    _revision_summary(db, row, current.revision_number)
                    for row in page.items
                ],
                "next_cursor": encode_cursor(page.next_cursor, key)
                if page.next_cursor
                else None,
            }
        )
    except ReportNotFound:
        raise ApiError("not_found", "Report not found.", status=404) from None
    except (InvalidCursor, ValueError):
        raise ApiError(
            "validation_failed", "Revision pagination is invalid.", status=400
        ) from None


@admin_reports_bp.get(
    "/<uuid:report_id>/revisions/<int:revision_number>",
    endpoint="revision_detail",
)
@_admin_get
def revision_detail_route(report_id: UUID, revision_number: int):
    db = current_request_session()
    try:
        current = get_report_admin(db, report_id)
        row = get_report_revision_admin(db, report_id, revision_number)
        _append_admin_view_audit(db, report_id)
        return success(
            {
                **_revision_summary(db, row, current.revision_number),
                "content": report_revision_content(row),
            }
        )
    except (ReportNotFound, ReportRevisionNotFound):
        raise ApiError("not_found", "Report not found.", status=404) from None


def _admin_mutation(purpose: str | None, operation):
    """Consume any purpose-scoped step-up, run `operation`, and commit once.

    `operation` performs its own ID-06 idempotency claim/complete via the
    persistence-layer *_record function it calls, so the step-up consumption
    above and the idempotency claim/complete/revision/audit writes inside
    `operation` all land in this single transaction.
    """
    actor = current_actor()
    db = current_request_session()
    now = datetime.now(UTC)
    try:
        if purpose is not None:
            pending = getattr(g, "pending_step_up", None)
            if not pending or pending[0] != purpose:
                raise StepUpRequired("Administrator PIN confirmation is required.")
            consume_step_up(
                db, actor=actor, raw_token=pending[1], purpose=purpose, now=now
            )
        view = operation(db, actor, now)
        db.commit()
        return success(_view_data(db, view))
    except StepUpRequired as error:
        db.rollback()
        raise ApiError("step_up_required", str(error), status=403) from None
    except AdminElevationRequired as error:
        db.rollback()
        raise ApiError("admin_elevation_required", str(error), status=403) from None
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
            "The report changed; reload before saving.",
            status=409,
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
    except ApiError:
        db.rollback()
        raise
    except (ValidationError, ValueError, TypeError):
        db.rollback()
        raise ApiError(
            "validation_failed", "The admin report request is invalid.", status=400
        ) from None
    except IntegrityError:
        db.rollback()
        raise ApiError(
            "revision_conflict",
            "The report changed; reload before saving.",
            status=409,
        ) from None
    except OperationalError as error:
        db.rollback()
        sqlstate = getattr(getattr(error, "orig", None), "sqlstate", None)
        if sqlstate in {"40P01", "40001", "55P03"}:
            raise ApiError(
                "revision_conflict",
                "The report changed; reload before saving.",
                status=409,
            ) from None
        raise ApiError(
            "dependency_unavailable",
            "The Admin service is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db.rollback()
        raise ApiError(
            "dependency_unavailable",
            "The Admin service is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@admin_reports_bp.patch("/<uuid:report_id>", endpoint="edit")
@require_access_token
@_require_admin_hidden
@require_compatible_write
@require_admin_elevation
def edit_route(report_id: UUID):
    payload = _body(exact={"content", "base_revision_number"})
    try:
        model = SaveReportRequest.model_validate_json(json.dumps(payload))
    except ValidationError:
        raise ApiError(
            "validation_failed", "The admin report request is invalid.", status=400
        ) from None

    def operation(db, actor, _now):
        return save_report_admin_record(
            db,
            actor,
            report_id,
            model,
            request.headers.get("Idempotency-Key", ""),
            request_id=request_id(),
            client_version=str(g.client_version),
            audit_writer=current_app.config["AUDIT_WRITER"],
        )

    return _admin_mutation(None, operation)


@admin_reports_bp.post("/<uuid:report_id>/restore", endpoint="restore")
@require_access_token
@_require_admin_hidden
@require_compatible_write
@require_step_up("report_restore")
@require_admin_elevation
def restore_route(report_id: UUID):
    payload = _body(exact={"revision_number"})
    revision_number = payload["revision_number"]
    if (
        not isinstance(revision_number, int)
        or isinstance(revision_number, bool)
        or revision_number < 1
    ):
        raise ApiError(
            "validation_failed", "The admin report request is invalid.", status=400
        )

    def operation(db, actor, _now):
        return restore_report_admin_record(
            db,
            actor,
            report_id,
            revision_number,
            request.headers.get("Idempotency-Key", ""),
            request_id=request_id(),
            client_version=str(g.client_version),
            audit_writer=current_app.config["AUDIT_WRITER"],
        )

    return _admin_mutation("report_restore", operation)


@admin_reports_bp.post("/<uuid:report_id>/transfer", endpoint="transfer")
@require_access_token
@_require_admin_hidden
@require_compatible_write
@require_step_up("report_transfer")
@require_admin_elevation
def transfer_route(report_id: UUID):
    payload = _body(allowed={"new_owner_staff_id", "new_preparer_staff_id", "reason"})
    if "new_owner_staff_id" not in payload or "reason" not in payload:
        raise ApiError(
            "validation_failed", "The admin report request is invalid.", status=400
        )
    reason = payload["reason"]
    if (
        not isinstance(reason, str)
        or not reason.strip()
        or len(reason) > TRANSFER_REASON_MAX_LENGTH
    ):
        raise ApiError(
            "validation_failed", "The admin report request is invalid.", status=400
        )
    try:
        new_owner_staff_id = UUID(str(payload["new_owner_staff_id"]))
        new_preparer_staff_id = (
            UUID(str(payload["new_preparer_staff_id"]))
            if payload.get("new_preparer_staff_id") is not None
            else None
        )
    except (TypeError, ValueError):
        raise ApiError(
            "validation_failed", "The admin report request is invalid.", status=400
        ) from None

    def operation(db, actor, _now):
        return transfer_report_ownership_record(
            db,
            actor,
            report_id,
            new_owner_staff_id,
            new_preparer_staff_id,
            reason,
            request.headers.get("Idempotency-Key", ""),
            request_id=request_id(),
            client_version=str(g.client_version),
            audit_writer=current_app.config["AUDIT_WRITER"],
        )

    return _admin_mutation("report_transfer", operation)


BULK_EXPORT_BODY_FIELDS = {"selection", "revision_selection", "reason"}
BULK_EXPORT_REASON_MAX_LENGTH = 500


@admin_reports_bp.post("/<uuid:report_id>/export-docx", endpoint="export_docx")
@require_access_token
@_require_admin_hidden
@require_admin_elevation
def admin_export_docx_route(report_id: UUID):
    """Export one explicit, immutable revision of any report, as an Admin.

    Same deterministic bytes as the officer's own export; a *different* audit
    action, because an administrator reading another employee's report is the
    event oversight cares about.
    """
    g.api_action = "admin_report_export"
    revision_number = export_revision_query()
    key = export_idempotency_key()
    db = current_request_session()
    try:
        view = get_report_admin(db, report_id)
        revision = get_report_revision_admin(db, report_id, revision_number)
        document = perform_single_export(
            db,
            actor=current_actor(),
            report=view.report,
            revision=revision,
            request_id=request_id(),
            idempotency_key=key,
            idempotency_action="admin.report_export_docx",
            audit_action="report.exported_by_admin",
            audit_writer=current_app.config["AUDIT_WRITER"],
            client_version=str(g.client_version),
            now=datetime.now(UTC),
        )
        db.commit()
    except RequestInProgress as error:
        db.rollback()
        raise ApiError(
            "request_in_progress", str(error), status=409, retryable=True
        ) from None
    except IdempotencyConflict as error:
        db.rollback()
        raise ApiError("idempotency_conflict", str(error), status=409) from None
    except (ReportNotFound, ReportRevisionNotFound):
        db.rollback()
        raise ApiError("not_found", "Report not found.", status=404) from None
    except ApiError:
        db.rollback()
        raise
    except (ValidationError, ValueError, TypeError):
        db.rollback()
        raise ApiError(
            "validation_failed", "The export request is invalid.", status=400
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError, OSError):
        db.rollback()
        raise ApiError(
            "dependency_unavailable",
            "The Admin service is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    response = stream_export(
        data=document.data,
        mime_type=EXPORT_MIME_TYPE,
        name=document.download_name,
        sha256=document.sha256,
        export_id=document.export_id,
        template_version_value=document.template_version,
        revision_number=document.revision_number,
    )
    response.headers["X-Request-ID"] = request_id()
    return response


def _bulk_reason(payload: dict) -> str:
    reason = payload.get("reason")
    if (
        not isinstance(reason, str)
        or not reason.strip()
        or len(reason) > BULK_EXPORT_REASON_MAX_LENGTH
    ):
        raise ApiError(
            "validation_failed", "A bulk export reason is required.", status=400
        )
    return reason


def _bulk_report_ids(selection: dict) -> tuple[UUID, ...]:
    raw = selection.get("report_ids")
    if not isinstance(raw, list) or not raw:
        raise ApiError(
            "validation_failed", "The bulk export selection is invalid.", status=400
        )
    if len(raw) > BULK_EXPORT_MAX_DOCUMENTS:
        raise ApiError(
            "bulk_export_limit_exceeded",
            f"A bulk export is limited to {BULK_EXPORT_MAX_DOCUMENTS} documents.",
            status=409,
        )
    ids: list[UUID] = []
    for item in raw:
        if not isinstance(item, str):
            raise ApiError(
                "validation_failed", "The bulk export selection is invalid.", status=400
            )
        try:
            parsed = UUID(item)
        except (AttributeError, TypeError, ValueError):
            raise ApiError(
                "validation_failed",
                "The bulk export selection is invalid.",
                status=400,
            ) from None
        ids.append(parsed)
    if len(set(ids)) != len(ids):
        raise ApiError(
            "validation_failed", "The bulk export selection is invalid.", status=400
        )
    return tuple(ids)


def _bulk_filters(selection: dict) -> AdminReportFilters:
    raw = selection.get("filters")
    if (
        not isinstance(raw, dict)
        or not raw
        or not set(raw) <= set(ADMIN_REPORT_FILTER_FIELDS)
    ):
        raise ApiError(
            "validation_failed", "The bulk export selection is invalid.", status=400
        )
    values: dict[str, str] = {}
    for name, value in raw.items():
        if not isinstance(value, str):
            raise ApiError(
                "validation_failed", "The bulk export selection is invalid.", status=400
            )
        values[name] = value
    try:
        filters = _filters_from_raw(values)
    except ValueError:
        raise ApiError(
            "validation_failed",
            "The bulk export selection is invalid.",
            status=400,
        ) from None
    for lo_name, hi_name in _RANGE_PAIRS:
        lo, hi = getattr(filters, lo_name), getattr(filters, hi_name)
        if lo is not None and hi is not None and lo > hi:
            raise ApiError(
                "validation_failed", "The bulk export selection is invalid.", status=400
            )
    return filters


def _bulk_selection(payload: dict):
    """Validate the closed, single-branch bulk selection body.

    Exactly one of two branches, `revision_selection` fixed to
    `current_at_request`, and no client-supplied limit: an operator asks for a
    named set of records, not for "as many as you can give me".
    """
    if set(payload) != BULK_EXPORT_BODY_FIELDS:
        raise ApiError(
            "validation_failed", "The bulk export request is invalid.", status=400
        )
    if payload.get("revision_selection") != BULK_REVISION_SELECTION:
        raise ApiError(
            "validation_failed", "The bulk export request is invalid.", status=400
        )
    reason = _bulk_reason(payload)
    selection = payload.get("selection")
    if not isinstance(selection, dict):
        raise ApiError(
            "validation_failed", "The bulk export selection is invalid.", status=400
        )
    mode = selection.get("mode")
    if mode == "report_ids":
        if set(selection) != {"mode", "report_ids"}:
            raise ApiError(
                "validation_failed", "The bulk export selection is invalid.", status=400
            )
        return "report_ids", _bulk_report_ids(selection), [], reason
    if mode == "filters":
        if set(selection) != {"mode", "filters"}:
            raise ApiError(
                "validation_failed", "The bulk export selection is invalid.", status=400
            )
        filters = _bulk_filters(selection)
        names = sorted(
            name
            for name in ADMIN_REPORT_FILTER_FIELDS
            if getattr(filters, name) is not None
        )
        return "filters", filters, names, reason
    raise ApiError(
        "validation_failed", "The bulk export selection is invalid.", status=400
    )


def _current_revisions(db, report_ids):
    rows = db.execute(
        select(Report, ReportRevision)
        .join(
            ReportRevision,
            and_(
                ReportRevision.report_id == Report.id,
                ReportRevision.revision_number == Report.current_revision_number,
            ),
        )
        .where(Report.id.in_(list(report_ids)))
    ).all()
    return {row[0].id: (row[0], row[1]) for row in rows}


def _resolve_bulk_selection(db, mode, selection):
    """Resolve and bound the selection *before* any document is generated."""
    if mode == "report_ids":
        found = _current_revisions(db, selection)
        missing = tuple(item for item in selection if item not in found)
        resolved = [found[item] for item in selection if item in found]
    else:

        class _SelectionAuditSink:
            """Bulk selection is internal, so it must not write a search audit."""

            @staticmethod
            def append(*_args, **_kwargs):
                return None

        page = admin_search_reports(
            db,
            selection,
            limit=BULK_EXPORT_MAX_DOCUMENTS + 1,
            cursor=None,
            sort="updated_at_desc",
            actor=current_actor(),
            request_id=request_id(),
            client_version=str(g.client_version),
            audit_writer=_SelectionAuditSink(),
        )
        if len(page.items) > BULK_EXPORT_MAX_DOCUMENTS:
            raise ApiError(
                "bulk_export_limit_exceeded",
                f"A bulk export is limited to {BULK_EXPORT_MAX_DOCUMENTS} documents.",
                status=409,
            )
        found = _current_revisions(db, [item.report.id for item in page.items])
        missing = ()
        resolved = list(found.values())
    if not resolved and not missing:
        raise ApiError(
            "not_found", "No reports matched the export selection.", status=404
        )
    resolved.sort(key=lambda pair: str(pair[0].id))
    return resolved, tuple(sorted(missing, key=str))


@admin_reports_bp.post("/bulk-export", endpoint="bulk_export")
@require_access_token
@_require_admin_hidden
@require_step_up("bulk_export")
@require_admin_elevation
def bulk_export_route():
    """Export a bounded, atomically resolved set of report revisions.

    The selection is resolved and persisted inside one repeatable-read
    transaction before the first document is generated, so the archive answers
    a single point in time; a report saved mid-export cannot slide a newer
    revision into the manifest.
    """
    g.api_action = "admin_report_bulk_export"
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError(
            "validation_failed", "The bulk export request is invalid.", status=400
        )
    mode, selection, filter_names, reason = _bulk_selection(payload)
    key = export_idempotency_key()
    actor = current_actor()
    db = current_request_session()
    now = datetime.now(UTC)
    try:
        pending = getattr(g, "pending_step_up", None)
        if not pending or pending[0] != "bulk_export":
            raise StepUpRequired("Administrator PIN confirmation is required.")
        # Close the authentication/elevation transaction so the selection can
        # run at REPEATABLE READ; everything below commits or rolls back as one.
        db.commit()
        db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
        consume_step_up(
            db, actor=actor, raw_token=pending[1], purpose="bulk_export", now=now
        )
        claim = claim_idempotency(
            session=db,
            actor=actor,
            key=key,
            action="admin.bulk_export",
            request_sha256=request_digest(
                {
                    "action": "admin.bulk_export",
                    "mode": mode,
                    "reason": reason,
                    "selection": (
                        sorted(str(item) for item in selection)
                        if mode == "report_ids"
                        else {
                            name: str(getattr(selection, name)) for name in filter_names
                        }
                    ),
                }
            ),
            now=now,
        )
        record = db.get(IdempotencyRecord, claim.record_id)
        if record is None:
            raise RuntimeError("bulk export idempotency record is unavailable")
        if claim.replayed:
            revision_ids, replay_failures = decode_bulk_reference(
                dict(record.response_reference)
            )
            rows = db.execute(
                select(Report, ReportRevision)
                .join(
                    ReportRevision,
                    ReportRevision.report_id == Report.id,
                )
                .where(ReportRevision.id.in_(list(revision_ids)))
            ).all()
            resolved = sorted(
                ((row[0], row[1]) for row in rows), key=lambda pair: str(pair[0].id)
            )
            known = tuple(
                ExportFailure(
                    report_id=item[0], revision_number=item[1], reason_code=item[2]
                )
                for item in replay_failures
            )
        else:
            resolved, missing = _resolve_bulk_selection(db, mode, selection)
            known = tuple(
                ExportFailure(
                    report_id=item, revision_number=None, reason_code="not_found"
                )
                for item in missing
            )
            # Persist the bounded selection before the first document exists.
            record.response_reference = {
                "format": "docx_zip",
                "ok": ",".join(revision.id.hex for _report, revision in resolved),
                "failed": ",".join(f"{item.hex}n0" for item in missing),
                "report_count": len(resolved),
            }
            db.flush()
        result = export_reports_zip(
            db,
            actor=actor,
            selections=resolved,
            known_failures=known,
            request_id=request_id(),
            idempotency_record_id=claim.record_id,
            reason=reason,
            filter_names=filter_names,
            selection_mode=mode,
            recorded_at=record.created_at,
            persist=not claim.replayed,
        )
        if not claim.replayed:
            current_app.config["AUDIT_WRITER"].append(
                db,
                AuditEventInput(
                    actor_account_id=actor.account_id,
                    actor_staff_member_id=actor.staff_member_id,
                    action="admin.bulk_exported",
                    result="success",
                    request_id=request_id(),
                    target_type="report",
                    target_id=None,
                    details={
                        "export_id": str(result.export_id),
                        "report_count": len(result.documents),
                    },
                    client_version=str(g.client_version),
                ),
            )
            complete_idempotency(
                db,
                claim,
                response_status=200,
                response_reference=bulk_reference(result),
                now=now,
            )
        db.commit()
    except StepUpRequired as error:
        db.rollback()
        raise ApiError("step_up_required", str(error), status=403) from None
    except AdminElevationRequired as error:
        db.rollback()
        raise ApiError("admin_elevation_required", str(error), status=403) from None
    except RequestInProgress as error:
        db.rollback()
        raise ApiError(
            "request_in_progress", str(error), status=409, retryable=True
        ) from None
    except IdempotencyConflict as error:
        db.rollback()
        raise ApiError("idempotency_conflict", str(error), status=409) from None
    except ApiError:
        db.rollback()
        raise
    except (ReportNotFound, ReportRevisionNotFound):
        db.rollback()
        raise ApiError("not_found", "Report not found.", status=404) from None
    except (ValidationError, ValueError, TypeError):
        db.rollback()
        raise ApiError(
            "validation_failed", "The bulk export request is invalid.", status=400
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError, OSError):
        db.rollback()
        raise ApiError(
            "dependency_unavailable",
            "The Admin service is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    response = stream_export(
        data=result.data,
        mime_type=BULK_EXPORT_MIME_TYPE,
        name=result.download_name,
        sha256=result.sha256,
        export_id=result.export_id,
        template_version_value=result.template_version,
    )
    response.headers["X-Request-ID"] = request_id()
    return response
