"""Incident-scoped report editor, history, copy, and document-export routes."""
from datetime import UTC, datetime
import json
import re
from uuid import UUID

from flask import Blueprint, current_app, g, request
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import aliased

from backend.forms.output_events import allowed_report_actions
from backend.identity.idempotency import IdempotencyConflict, RequestInProgress
from backend.persistence.database import DatabaseUnavailable
from backend.persistence.models.identity import StaffMember
from backend.persistence.models.reporting import Report, ReportAccess, ReportRevision
from backend.reports.export_service import (
    EXPORT_MIME_TYPE,
    perform_single_export,
    stream_export,
)
from backend.reports.persistence import (
    IncidentNotFound,
    ReportNotFound,
    ReportRevisionNotFound,
    ReportView,
    get_incident,
    get_report,
    get_report_admin,
    get_report_revision,
    get_report_revision_admin,
    list_report_revisions,
    list_report_revisions_admin,
    report_revision_content,
    restore_report_record,
    save_report_record,
)
from backend.reports.revisions import RevisionConflict, RevisionTargetMissing
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.pagination import InvalidCursor, decode_cursor, encode_cursor
from backend.webapp.api_v1.responses import success
from backend.webapp.api_v1.schemas.reporting import SaveReportRequest
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


reports_bp = Blueprint("web_reports", __name__)
_EXPORT_REVISION_PATTERN = re.compile(r"^[1-9][0-9]{0,8}$")


def _load_report(db, report_id: UUID) -> ReportView:
    actor = current_browser_actor()
    if actor.role == "admin":
        return get_report_admin(db, report_id)
    return get_report(db, actor, report_id)


def _load_report_revision(db, report_id: UUID, revision_number: int):
    actor = current_browser_actor()
    if actor.role == "admin":
        return get_report_revision_admin(db, report_id, revision_number)
    return get_report_revision(db, actor, report_id, revision_number)


def _presentation(report_type) -> tuple[str, list[str]]:
    value = getattr(report_type, "value", report_type)
    actions = sorted(allowed_report_actions(value))
    return ("copy_text" if "copy_text" in actions else "document", actions)


def _staff(db, staff_id: UUID) -> dict[str, str | None]:
    row = db.get(StaffMember, staff_id)
    if row is None:
        raise RuntimeError("report staff is unavailable")
    return {
        "staff_id": str(row.id),
        "employee_number": row.employee_number,
        "display_name": " ".join(
            part for part in (row.rank, row.first_name, row.last_name) if part
        ),
        "rank": row.rank,
        "shift": row.shift,
    }


def _current_revision(db, report: Report) -> ReportRevision:
    revision = db.scalar(select(ReportRevision).where(
        ReportRevision.report_id == report.id,
        ReportRevision.revision_number == report.current_revision_number,
    ))
    if revision is None:
        raise ReportNotFound("Report not found.")
    return revision


def _view_data(db, view: ReportView) -> dict[str, object]:
    report = view.report
    presentation, actions = _presentation(report.report_type)
    revision = _current_revision(db, report)
    source_revision = None
    if revision.source_incident_revision_id is not None:
        source = revision.provenance or {}
        value = source.get("source_revision_number")
        source_revision = value if isinstance(value, int) else None
    return {
        "report_id": str(report.id),
        "incident_id": str(report.incident_id),
        "report_type": getattr(report.report_type, "value", report.report_type),
        "presentation": presentation,
        "allowed_actions": actions,
        "status": view.status,
        "current_revision_number": view.revision_number,
        "source_incident_revision_number": source_revision,
        "content": view.content,
        "reporting_officer": _staff(db, report.reporting_staff_member_id),
        "preparer": _staff(db, report.prepared_by_staff_member_id),
        "last_editor_staff_member_id": str(view.editor_staff_member_id),
        "last_editor_display_name": view.editor_display_name,
        "created_at": timestamp(report.created_at),
        "updated_at": timestamp(view.updated_at),
    }


def _revision_summary(db, row, current_revision_number: int) -> dict[str, object]:
    editor = _staff(db, row.editor_staff_member_id)
    source = row.provenance or {}
    source_number = source.get("source_revision_number")
    return {
        "revision_id": str(row.id),
        "revision_number": row.revision_number,
        "reason": row.reason,
        "changed_fields": list((row.changed_fields or {}).get("fields", [])),
        "editor_staff_member_id": editor["staff_id"],
        "editor_display_name": editor["display_name"],
        "source_incident_revision_number": source_number
        if isinstance(source_number, int)
        else None,
        "client_version": row.client_version,
        "created_at": timestamp(row.created_at),
        "is_current": row.revision_number == current_revision_number,
    }


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
            "The report changed; your local text has been preserved.",
            status=409,
            details={
                "current_revision_number": error.current_revision_number,
                "current_editor_display_name": error.current_editor_display_name,
                "current_edited_at": timestamp(error.updated_at),
                "changed_fields": list(error.changed_fields),
            },
        ) from None
    except (ReportNotFound, ReportRevisionNotFound, RevisionTargetMissing):
        db.rollback()
        raise ApiError("not_found", "Report not found.", status=404) from None
    except (ValidationError, ValueError, TypeError):
        db.rollback()
        raise ApiError(
            "validation_failed", "The report request is invalid.", status=400
        ) from None
    except IntegrityError:
        db.rollback()
        raise ApiError(
            "revision_conflict",
            "The report changed; your local text has been preserved.",
            status=409,
        ) from None
    except OperationalError as error:
        db.rollback()
        sqlstate = getattr(getattr(error, "orig", None), "sqlstate", None)
        if sqlstate in LOCK_CONFLICT_STATES:
            raise ApiError(
                "revision_conflict",
                "The report changed; your local text has been preserved.",
                status=409,
            ) from None
        raise ApiError(
            "dependency_unavailable",
            "Report storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db.rollback()
        raise ApiError(
            "dependency_unavailable",
            "Report storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@reports_bp.get("/incidents/<uuid:incident_id>/reports")
@require_browser_session
def list_incident_reports(incident_id: UUID):
    try:
        db = current_browser_session()
        actor = current_browser_actor()
        get_incident(db, actor, incident_id)
        owner = aliased(StaffMember)
        preparer = aliased(StaffMember)
        statement = (
            select(Report, owner, preparer)
            .join(owner, owner.id == Report.reporting_staff_member_id)
            .join(preparer, preparer.id == Report.prepared_by_staff_member_id)
            .where(Report.incident_id == incident_id)
        )
        if actor.role != "admin":
            statement = statement.join(
                ReportAccess, ReportAccess.report_id == Report.id
            ).where(
                ReportAccess.staff_member_id == actor.staff_member_id,
                ReportAccess.revoked_at.is_(None),
            )
        rows = db.execute(statement.order_by(Report.report_type, Report.id)).all()
        items = []
        seen: set[UUID] = set()
        for report, owner_row, preparer_row in rows:
            if report.id in seen:
                continue
            seen.add(report.id)
            presentation, actions = _presentation(report.report_type)
            items.append({
                "report_id": str(report.id),
                "incident_id": str(report.incident_id),
                "report_type": getattr(report.report_type, "value", report.report_type),
                "presentation": presentation,
                "allowed_actions": actions,
                "status": report.status,
                "current_revision_number": report.current_revision_number,
                "reporting_officer": {
                    "staff_id": str(owner_row.id),
                    "display_name": " ".join(
                        part for part in (
                            owner_row.rank, owner_row.first_name, owner_row.last_name
                        ) if part
                    ),
                },
                "preparer": {
                    "staff_id": str(preparer_row.id),
                    "display_name": " ".join(
                        part for part in (
                            preparer_row.rank,
                            preparer_row.first_name,
                            preparer_row.last_name,
                        ) if part
                    ),
                },
                "updated_at": timestamp(report.updated_at),
            })
        return success({"items": items})
    except (IncidentNotFound, ReportNotFound):
        raise ApiError("not_found", "Incident not found.", status=404) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Report storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@reports_bp.get("/reports/<uuid:report_id>")
@require_browser_session
def get_report_route(report_id: UUID):
    try:
        db = current_browser_session()
        return success(_view_data(db, _load_report(db, report_id)))
    except ReportNotFound:
        raise ApiError("not_found", "Report not found.", status=404) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Report storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@reports_bp.patch("/reports/<uuid:report_id>")
@require_browser_session
@require_browser_csrf
def save_report_route(report_id: UUID):
    payload = json_body(
        allowed={"content", "base_revision_number", "reason"},
        required={"content", "base_revision_number"},
        message="The report request is invalid.",
    )
    try:
        model = SaveReportRequest.model_validate_json(json.dumps(payload))
    except ValidationError:
        raise ApiError(
            "validation_failed", "The report request is invalid.", status=400
        ) from None
    validate_if_match(model.base_revision_number)
    req_id, version = request_metadata()
    return _write(lambda db: save_report_record(
        db,
        current_browser_actor(),
        report_id,
        model,
        require_idempotency_key(),
        request_id=req_id,
        client_version=version,
        audit_writer=current_app.config["AUDIT_WRITER"],
    ))


@reports_bp.get("/reports/<uuid:report_id>/revisions")
@require_browser_session
def list_report_revisions_route(report_id: UUID):
    try:
        if not set(request.args) <= {"limit", "cursor"}:
            raise ValueError
        raw_limit = request.args.get("limit", "50")
        limit = int(raw_limit)
        if str(limit) != raw_limit.strip() or not 1 <= limit <= 100:
            raise ValueError
        db = current_browser_session()
        current = _load_report(db, report_id)
        key = current_app.config["IDENTITY_SETTINGS"].cursor_signing_key
        if not key:
            raise RuntimeError("report pagination key is unavailable")
        raw_cursor = request.args.get("cursor")
        cursor = decode_cursor(raw_cursor, key) if raw_cursor else None
        if current_browser_actor().role == "admin":
            page = list_report_revisions_admin(
                db, report_id, limit=limit, cursor=cursor
            )
        else:
            page = list_report_revisions(
                db,
                current_browser_actor(),
                report_id,
                limit=limit,
                cursor=cursor,
            )
        return success({
            "items": [
                _revision_summary(db, row, current.revision_number)
                for row in page.items
            ],
            "next_cursor": encode_cursor(page.next_cursor, key)
            if page.next_cursor
            else None,
        })
    except (InvalidCursor, ValueError):
        raise ApiError(
            "validation_failed", "Revision pagination is invalid.", status=400
        ) from None
    except ReportNotFound:
        raise ApiError("not_found", "Report not found.", status=404) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Report storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@reports_bp.get("/reports/<uuid:report_id>/revisions/<int:revision_number>")
@require_browser_session
def get_report_revision_route(report_id: UUID, revision_number: int):
    try:
        db = current_browser_session()
        current = _load_report(db, report_id)
        row = _load_report_revision(db, report_id, revision_number)
        return success({
            **_revision_summary(db, row, current.revision_number),
            "content": report_revision_content(row),
        })
    except (ReportNotFound, ReportRevisionNotFound):
        raise ApiError("not_found", "Report not found.", status=404) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "Report storage is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@reports_bp.post("/reports/<uuid:report_id>/restore")
@require_browser_session
@require_browser_csrf
def restore_report_route(report_id: UUID):
    payload = json_body(
        exact={"revision_number"}, message="The restore request is invalid."
    )
    revision_number = payload["revision_number"]
    if not isinstance(revision_number, int) or isinstance(revision_number, bool):
        raise ApiError(
            "validation_failed", "The restore request is invalid.", status=400
        )
    req_id, version = request_metadata()
    return _write(lambda db: restore_report_record(
        db,
        current_browser_actor(),
        report_id,
        revision_number,
        require_idempotency_key(),
        request_id=req_id,
        client_version=version,
        audit_writer=current_app.config["AUDIT_WRITER"],
    ))


def _export_revision() -> int:
    values = request.args.getlist("revision")
    if set(request.args) != {"revision"} or len(values) != 1:
        raise ApiError(
            "validation_failed", "An explicit revision is required.", status=400
        )
    if not _EXPORT_REVISION_PATTERN.fullmatch(values[0]) or request.get_data(cache=True):
        raise ApiError(
            "validation_failed", "An explicit revision is required.", status=400
        )
    return int(values[0])


@reports_bp.post("/reports/<uuid:report_id>/export-docx")
@require_browser_session
@require_browser_csrf
def export_report_route(report_id: UUID):
    g.api_action = "report_export"
    revision_number = _export_revision()
    db = current_browser_session()
    try:
        view = _load_report(db, report_id)
        if "download_word" not in allowed_report_actions(view.report.report_type):
            raise ApiError(
                "action_not_allowed",
                "This report is copy-only and cannot be downloaded.",
                status=409,
            )
        revision = _load_report_revision(db, report_id, revision_number)
        req_id, version = request_metadata()
        document = perform_single_export(
            db,
            actor=current_browser_actor(),
            report=view.report,
            revision=revision,
            request_id=req_id,
            idempotency_key=require_idempotency_key(),
            idempotency_action="report.export_docx",
            audit_action="report.exported",
            audit_writer=current_app.config["AUDIT_WRITER"],
            client_version=version,
            now=datetime.now(UTC),
        )
        db.commit()
    except ApiError:
        db.rollback()
        raise
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
    except (ValidationError, ValueError, TypeError):
        db.rollback()
        raise ApiError(
            "validation_failed", "The export request is invalid.", status=400
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError, OSError):
        db.rollback()
        raise ApiError(
            "dependency_unavailable",
            "Report export is temporarily unavailable.",
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
    response.headers["X-Request-ID"] = str(g.request_id)
    return response
