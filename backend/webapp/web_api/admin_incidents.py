"""Administrator incident-centered browser API."""
from copy import deepcopy
from datetime import UTC, date, datetime
from uuid import UUID

from flask import Blueprint, current_app, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from backend.identity.audit import AuditEventInput
from backend.identity.browser_admin import (
    BrowserAdminStepUpRequired,
    consume_browser_admin_step_up,
    require_browser_admin_elevation,
)
from backend.identity.config import IdentitySettings
from backend.identity.elevation import AdminElevationRequired
from backend.identity.idempotency import (
    IdempotencyConflict,
    RequestInProgress,
    claim_idempotency,
    complete_idempotency,
    request_digest,
)
from backend.persistence.database import DatabaseUnavailable
from backend.persistence.models.identity import StaffMember
from backend.persistence.models.reporting import Incident, IncidentRevision, Report
from backend.reports.admin_incidents import (
    AdminIncidentFilters,
    AdminIncidentSummary,
    list_admin_incident_summaries,
)
from backend.reports.persistence import (
    IncidentNotFound,
    IncidentRevisionNotFound,
    ReportNotFound,
    get_incident,
    restore_incident_record,
    transfer_report_ownership_record,
)
from backend.reports.revisions import RevisionConflict, RevisionTargetMissing
from backend.webapp.api_v1.context import request_id
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.pagination import InvalidCursor, decode_cursor, encode_cursor
from backend.webapp.api_v1.responses import success
from backend.webapp.web_api.admin_auth import (
    ADMIN_STEP_UP_COOKIE,
    ADMIN_STEP_UP_COOKIE_PATH,
)
from backend.webapp.web_api.auth import _is_https
from backend.webapp.web_api.middleware import (
    current_browser_actor,
    current_browser_session,
    require_browser_csrf,
    require_browser_role,
    require_browser_session,
)


admin_incidents_bp = Blueprint("web_admin_incidents", __name__)
_ALLOWED_QUERY_KEYS = {
    "q",
    "incident_number",
    "reporting_staff_id",
    "prepared_by_staff_id",
    "incident_date_from",
    "incident_date_to",
    "created_at_from",
    "created_at_to",
    "category",
    "facility",
    "location",
    "shift",
    "records_status",
    "last_editor_staff_id",
    "updated_at_from",
    "updated_at_to",
    "limit",
    "cursor",
}
_RECORDS_STATUSES = {"in_progress", "completed", "archived"}
_REASON_MAX_LENGTH = 500


def _validation_error() -> ApiError:
    return ApiError(
        "validation_failed",
        "The administrator incident request is invalid.",
        status=400,
    )


def _single(name: str) -> str | None:
    values = request.args.getlist(name)
    if len(values) > 1:
        raise _validation_error()
    return values[0] if values else None


def _text(name: str, *, maximum: int = 200) -> str | None:
    raw = _single(name)
    if raw is None:
        return None
    value = " ".join(raw.split())
    if not value or len(value) > maximum:
        raise _validation_error()
    return value


def _uuid(name: str) -> UUID | None:
    raw = _single(name)
    if raw is None:
        return None
    try:
        return UUID(raw)
    except ValueError:
        raise _validation_error() from None


def _date(name: str) -> date | None:
    raw = _single(name)
    if raw is None:
        return None
    try:
        value = date.fromisoformat(raw)
    except ValueError:
        raise _validation_error() from None
    if value.isoformat() != raw:
        raise _validation_error()
    return value


def _datetime(name: str) -> datetime | None:
    raw = _single(name)
    if raw is None:
        return None
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        raise _validation_error() from None
    if value.tzinfo is None:
        raise _validation_error()
    return value.astimezone(UTC)


def _limit() -> int:
    raw = _single("limit")
    if raw is None:
        return 25
    if not raw.isascii() or not raw.isdigit() or str(int(raw)) != raw:
        raise _validation_error()
    value = int(raw)
    if not 1 <= value <= 50:
        raise _validation_error()
    return value


def _settings() -> IdentitySettings:
    settings = current_app.config.get("IDENTITY_SETTINGS")
    if not isinstance(settings, IdentitySettings) or not settings.cursor_signing_key:
        raise ApiError(
            "dependency_unavailable",
            "Administrator incident search is temporarily unavailable.",
            status=503,
            retryable=True,
        )
    return settings


def _cursor(settings: IdentitySettings) -> dict[str, str] | None:
    raw = _single("cursor")
    if raw is None:
        return None
    try:
        return decode_cursor(raw, settings.cursor_signing_key or "")
    except InvalidCursor:
        raise _validation_error() from None


def _timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _staff(value) -> dict[str, str]:
    return {"staff_id": str(value.staff_id), "display_name": value.display_name}


def _staff_row(db, staff_id: UUID) -> dict[str, str | None]:
    row = db.get(StaffMember, staff_id)
    if row is None:
        raise RuntimeError("administrator incident staff is unavailable")
    return {
        "staff_id": str(row.id),
        "employee_number": row.employee_number,
        "display_name": " ".join(
            part for part in (row.rank, row.first_name, row.last_name) if part
        ),
        "rank": row.rank,
        "shift": row.shift,
    }


def _summary(item: AdminIncidentSummary) -> dict[str, object]:
    return {
        "incident_id": str(item.incident_id),
        "incident_number": item.incident_number,
        "incident_name": item.incident_name,
        "incident_date": item.incident_date.isoformat() if item.incident_date else None,
        "category": item.category,
        "facility": item.facility,
        "location": item.location,
        "shift": item.shift,
        "records_status": item.records_status,
        "reporting_officers": [_staff(value) for value in item.reporting_officers],
        "preparers": [_staff(value) for value in item.preparers],
        "last_editor": _staff(item.last_editor) if item.last_editor else None,
        "progress": {
            "code": item.progress.code,
            "label": item.progress.label,
            "blocking_count": item.progress.blocking_count,
        },
        "officer_report_count": item.officer_report_count,
        "required_paperwork_count": item.required_paperwork_count,
        "created_at": _timestamp(item.created_at),
        "updated_at": _timestamp(item.updated_at),
    }


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


def _json_exact(fields: set[str]) -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != fields:
        raise _validation_error()
    return payload


def _reason(payload: dict) -> str:
    value = payload.get("reason")
    if not isinstance(value, str):
        raise _validation_error()
    cleaned = " ".join(value.split())
    if not cleaned or len(cleaned) > _REASON_MAX_LENGTH:
        raise _validation_error()
    return cleaned


def _consume_step_up(purpose: str) -> None:
    raw = request.cookies.get(ADMIN_STEP_UP_COOKIE, "")
    if not raw:
        raise ApiError(
            "step_up_required",
            "Administrator PIN confirmation is required.",
            status=403,
        )
    try:
        consume_browser_admin_step_up(
            current_browser_session(),
            actor=current_browser_actor(),
            raw_token=raw,
            purpose=purpose,
            now=datetime.now(UTC),
        )
    except BrowserAdminStepUpRequired:
        raise ApiError(
            "step_up_required",
            "Administrator PIN confirmation is required.",
            status=403,
        ) from None


def _clear_step_up(response):
    response.delete_cookie(
        ADMIN_STEP_UP_COOKIE,
        path=ADMIN_STEP_UP_COOKIE_PATH,
        secure=_is_https(),
        httponly=True,
        samesite="Lax",
    )
    return response


def _report_data(db, view) -> dict[str, object]:
    report = view.report
    return {
        "report_id": str(report.id),
        "incident_id": str(report.incident_id),
        "report_type": getattr(report.report_type, "value", report.report_type),
        "status": view.status,
        "current_revision_number": view.revision_number,
        "reporting_officer": _staff_row(db, report.reporting_staff_member_id),
        "preparer": _staff_row(db, report.prepared_by_staff_member_id),
        "last_editor_staff_member_id": str(view.editor_staff_member_id),
        "last_editor_display_name": view.editor_display_name,
        "updated_at": _timestamp(view.updated_at),
        "admin_attribution_required": True,
    }


def _incident_detail(db, incident_id: UUID) -> dict[str, object]:
    view = get_incident(db, current_browser_actor(), incident_id)
    incident = view.incident
    reports = list(db.scalars(
        select(Report)
        .where(Report.incident_id == incident_id)
        .order_by(Report.created_at, Report.id)
    ).all())
    preparer_ids = tuple(dict.fromkeys(
        report.prepared_by_staff_member_id for report in reports
    ))
    return {
        "incident_id": str(incident.id),
        "incident_number": incident.incident_number,
        "incident_name": incident.incident_name,
        "records_status": incident.status,
        "current_revision_number": incident.current_revision_number,
        "reporting_staff_ids": [str(value) for value in view.reporting_staff_ids],
        "reporting_officers": [
            _staff_row(db, value) for value in view.reporting_staff_ids
        ],
        "preparers": [_staff_row(db, value) for value in preparer_ids],
        "reports": [
            {
                "report_id": str(report.id),
                "report_type": getattr(report.report_type, "value", report.report_type),
                "status": report.status,
                "current_revision_number": report.current_revision_number,
                "reporting_officer": _staff_row(db, report.reporting_staff_member_id),
                "preparer": _staff_row(db, report.prepared_by_staff_member_id),
                "updated_at": _timestamp(report.updated_at),
            }
            for report in reports
        ],
        "field_notes": incident.field_notes,
        "incident_date": incident.incident_date.isoformat() if incident.incident_date else None,
        "incident_time": incident.incident_time.isoformat() if incident.incident_time else None,
        "facility": incident.facility,
        "shift": incident.shift,
        "location": incident.location,
        "category": incident.category,
        "classification": incident.classification,
        "extracted_facts": incident.extracted_facts,
        "gap_answers": incident.gap_answers,
        "charges": incident.charges,
        "validation": incident.validation,
        "created_at": _timestamp(incident.created_at),
        "updated_at": _timestamp(incident.updated_at),
        "admin_attribution_required": True,
    }


def _change_records_status(
    db,
    incident_id: UUID,
    *,
    records_status: str,
    base_revision_number: int,
) -> dict[str, object]:
    if records_status not in _RECORDS_STATUSES:
        raise ValueError("records status is invalid")
    if (
        not isinstance(base_revision_number, int)
        or isinstance(base_revision_number, bool)
        or base_revision_number < 1
    ):
        raise ValueError("base revision is invalid")
    actor = current_browser_actor()
    now = datetime.now(UTC)
    canonical = {
        "incident_id": str(incident_id),
        "records_status": records_status,
        "base_revision_number": base_revision_number,
    }
    claim = claim_idempotency(
        db,
        actor,
        key=request.headers.get("Idempotency-Key", ""),
        action="admin.incident_records_status",
        request_sha256=request_digest(canonical),
        now=now,
    )
    if claim.replayed:
        return _incident_detail(db, incident_id)

    incident = db.scalar(
        select(Incident).where(Incident.id == incident_id).with_for_update()
    )
    if incident is None:
        raise IncidentNotFound("Incident not found.")
    if incident.current_revision_number != base_revision_number:
        raise RevisionConflict(
            current_revision_number=incident.current_revision_number,
            status=incident.status,
            updated_at=incident.updated_at,
        )
    if incident.status == records_status:
        raise ValueError("records status is already set")
    source = db.scalar(select(IncidentRevision).where(
        IncidentRevision.incident_id == incident_id,
        IncidentRevision.revision_number == incident.current_revision_number,
    ))
    if source is None:
        raise IncidentRevisionNotFound("Incident revision not found.")

    old_status = incident.status
    next_revision = incident.current_revision_number + 1
    db.add(IncidentRevision(
        incident_id=incident.id,
        revision_number=next_revision,
        editor_account_id=actor.account_id,
        editor_staff_member_id=actor.staff_member_id,
        snapshot=deepcopy(source.snapshot),
        changed_fields={"fields": ["records_status"]},
        reason="status_change",
        client_version=request.headers.get("X-Client-Version", "1.0.0"),
        request_id=request_id(),
        created_at=now,
    ))
    incident.status = records_status
    incident.current_revision_number = next_revision
    incident.updated_at = now
    incident.archived_at = now if records_status == "archived" else None
    current_app.config["AUDIT_WRITER"].append(db, AuditEventInput(
        actor_account_id=actor.account_id,
        actor_staff_member_id=actor.staff_member_id,
        action="incident.status_changed",
        result="success",
        request_id=request_id(),
        target_type="incident",
        target_id=incident.id,
        details={
            "incident_id": str(incident.id),
            "old_status": old_status,
            "new_status": records_status,
        },
        client_version=request.headers.get("X-Client-Version"),
    ))
    complete_idempotency(
        db,
        claim,
        response_status=200,
        response_reference={
            "incident_id": str(incident.id),
            "records_status": records_status,
            "revision_number": next_revision,
        },
        now=now,
    )
    db.flush()
    return _incident_detail(db, incident_id)


def _write(operation, *, clear_step_up: bool = False):
    db = current_browser_session()
    try:
        data = operation(db)
        db.commit()
        response = success(data)
        return _clear_step_up(response) if clear_step_up else response
    except RequestInProgress as error:
        db.rollback()
        raise ApiError("request_in_progress", str(error), status=409, retryable=True) from None
    except IdempotencyConflict as error:
        db.rollback()
        raise ApiError("idempotency_conflict", str(error), status=409) from None
    except RevisionConflict as error:
        db.rollback()
        raise ApiError(
            "revision_conflict",
            "The incident changed; reload before saving.",
            status=409,
            details={
                "current_revision_number": error.current_revision_number,
                "current_edited_at": _timestamp(error.updated_at),
                "changed_fields": list(error.changed_fields),
            },
        ) from None
    except (IncidentNotFound, IncidentRevisionNotFound, ReportNotFound, RevisionTargetMissing):
        db.rollback()
        raise ApiError("not_found", "Administrator record not found.", status=404) from None
    except ApiError:
        db.rollback()
        raise
    except (ValueError, TypeError):
        db.rollback()
        raise _validation_error() from None
    except IntegrityError:
        db.rollback()
        raise ApiError(
            "revision_conflict",
            "The administrator record changed; reload and try again.",
            status=409,
        ) from None
    except OperationalError as error:
        db.rollback()
        sqlstate = getattr(getattr(error, "orig", None), "sqlstate", None)
        if sqlstate in {"40P01", "40001", "55P03"}:
            raise ApiError(
                "revision_conflict",
                "The administrator record changed; reload and try again.",
                status=409,
            ) from None
        raise ApiError(
            "dependency_unavailable",
            "Administrator incident storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db.rollback()
        raise ApiError(
            "dependency_unavailable",
            "Administrator incident storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@admin_incidents_bp.get("/incidents", endpoint="list_incidents")
@require_browser_session
@require_browser_role("admin")
def list_incidents_route():
    if set(request.args) - _ALLOWED_QUERY_KEYS:
        raise _validation_error()
    _require_elevation()
    settings = _settings()
    try:
        filters = AdminIncidentFilters(
            q=_text("q"),
            incident_number=_text("incident_number", maximum=11),
            reporting_staff_id=_uuid("reporting_staff_id"),
            prepared_by_staff_id=_uuid("prepared_by_staff_id"),
            incident_date_from=_date("incident_date_from"),
            incident_date_to=_date("incident_date_to"),
            created_at_from=_datetime("created_at_from"),
            created_at_to=_datetime("created_at_to"),
            category=_text("category", maximum=120),
            facility=_text("facility", maximum=120),
            location=_text("location", maximum=200),
            shift=_text("shift", maximum=32),
            records_status=_text("records_status", maximum=16),
            last_editor_staff_id=_uuid("last_editor_staff_id"),
            updated_at_from=_datetime("updated_at_from"),
            updated_at_to=_datetime("updated_at_to"),
        )
        page = list_admin_incident_summaries(
            current_browser_session(),
            current_browser_actor(),
            filters=filters,
            limit=_limit(),
            cursor=_cursor(settings),
        )
    except ApiError:
        raise
    except ValueError:
        raise _validation_error() from None
    except PermissionError:
        raise ApiError("permission_denied", "Permission denied.", status=403) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Administrator incident search is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None

    return success({
        "items": [_summary(item) for item in page.items],
        "next_cursor": (
            encode_cursor(page.next_cursor, settings.cursor_signing_key)
            if page.next_cursor else None
        ),
    })


@admin_incidents_bp.get("/incidents/<uuid:incident_id>", endpoint="incident_detail")
@require_browser_session
@require_browser_role("admin")
def incident_detail_route(incident_id: UUID):
    _require_elevation()
    try:
        return success(_incident_detail(current_browser_session(), incident_id))
    except IncidentNotFound:
        raise ApiError("not_found", "Incident not found.", status=404) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Administrator incident storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@admin_incidents_bp.patch(
    "/incidents/<uuid:incident_id>/records-status",
    endpoint="incident_records_status",
)
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def incident_records_status_route(incident_id: UUID):
    _require_elevation()
    payload = _json_exact({"records_status", "base_revision_number"})
    return _write(lambda db: _change_records_status(
        db,
        incident_id,
        records_status=payload["records_status"],
        base_revision_number=payload["base_revision_number"],
    ))


@admin_incidents_bp.post("/incidents/<uuid:incident_id>/restore", endpoint="incident_restore")
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def incident_restore_route(incident_id: UUID):
    _require_elevation()
    payload = _json_exact({"revision_number", "reason"})
    revision_number = payload.get("revision_number")
    if (
        not isinstance(revision_number, int)
        or isinstance(revision_number, bool)
        or revision_number < 1
    ):
        raise _validation_error()
    reason = _reason(payload)
    _consume_step_up("report_restore")

    def operation(db):
        view = restore_incident_record(
            db,
            current_browser_actor(),
            incident_id,
            revision_number,
            request.headers.get("Idempotency-Key", ""),
            request_id=request_id(),
            client_version=request.headers.get("X-Client-Version", "1.0.0"),
            audit_writer=current_app.config["AUDIT_WRITER"],
        )
        current_app.config["AUDIT_WRITER"].append(db, AuditEventInput(
            actor_account_id=current_browser_actor().account_id,
            actor_staff_member_id=current_browser_actor().staff_member_id,
            action="incident.restored",
            result="success",
            request_id=request_id(),
            target_type="incident",
            target_id=incident_id,
            details={
                "incident_id": str(incident_id),
                "revision_number": view.revision_number or 0,
                "source_revision_number": revision_number,
            },
            client_version=request.headers.get("X-Client-Version"),
        ))
        return _incident_detail(db, incident_id)

    return _write(operation, clear_step_up=True)


@admin_incidents_bp.post("/reports/<uuid:report_id>/transfer", endpoint="report_transfer")
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def report_transfer_route(report_id: UUID):
    _require_elevation()
    payload = _json_exact({"new_owner_staff_id", "new_preparer_staff_id", "reason"})
    reason = _reason(payload)
    try:
        new_owner_staff_id = UUID(str(payload["new_owner_staff_id"]))
        new_preparer_staff_id = (
            UUID(str(payload["new_preparer_staff_id"]))
            if payload.get("new_preparer_staff_id") is not None
            else None
        )
    except (TypeError, ValueError):
        raise _validation_error() from None
    _consume_step_up("report_transfer")

    def operation(db):
        view = transfer_report_ownership_record(
            db,
            current_browser_actor(),
            report_id,
            new_owner_staff_id,
            new_preparer_staff_id,
            reason,
            request.headers.get("Idempotency-Key", ""),
            request_id=request_id(),
            client_version=request.headers.get("X-Client-Version", "1.0.0"),
            audit_writer=current_app.config["AUDIT_WRITER"],
        )
        return _report_data(db, view)

    return _write(operation, clear_step_up=True)
