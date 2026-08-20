"""Bounded, content-free Operational Command Center summary."""
from dataclasses import dataclass
from datetime import UTC, date, datetime

from flask import Blueprint, request
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.identity.browser_admin import require_browser_admin_elevation
from backend.identity.elevation import AdminElevationRequired
from backend.persistence.database import DatabaseUnavailable
from backend.persistence.models.identity import Account
from backend.persistence.models.jobs import TaskOutbox
from backend.persistence.models.paperwork import PaperworkRecord
from backend.persistence.models.security import AuditEvent
from backend.paperwork.models import PaperworkKind, PaperworkView
from backend.reports.incident_library import (
    IncidentLibraryFilters,
    list_incident_summaries,
)
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.responses import success
from backend.webapp.web_api.middleware import (
    current_browser_actor,
    current_browser_session,
    require_browser_role,
    require_browser_session,
)
from backend.webapp.web_api.admin_daily_paperwork import daily_record_data


admin_overview_bp = Blueprint("web_admin_overview", __name__)


@dataclass(frozen=True)
class AdminOverview:
    todays_paperwork: dict[str, object]
    incidents_needing_attention: list[dict[str, object]]
    account_conditions: dict[str, int]
    system_availability: dict[str, str]
    recent_activity: list[dict[str, object]]


def _timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _paperwork_state(
    session: Session,
    *,
    kind: str,
    work_date: date,
    shift: str | None = None,
) -> dict[str, object]:
    statement = select(PaperworkRecord).where(
        PaperworkRecord.kind == kind,
        PaperworkRecord.work_date == work_date,
    )
    if shift is not None:
        statement = statement.where(PaperworkRecord.shift == shift)
    row = session.scalar(
        statement
        .order_by(PaperworkRecord.updated_at.desc(), PaperworkRecord.id.desc())
        .limit(1)
    )
    if row is None:
        return {
            "status": "not_started",
            "state": "not_started",
            "record_id": None,
            "revision": None,
            "warning_count": 0,
            "shift": shift,
            "updated_at": None,
        }
    summary = daily_record_data(PaperworkView(
        record_id=row.id,
        kind=PaperworkKind(row.kind),
        work_date=row.work_date,
        shift=row.shift,
        current_revision_number=row.current_revision_number,
        payload=dict(row.current_payload or {}),
        created_by_staff_member_id=row.created_by_staff_member_id,
        last_editor_staff_member_id=row.last_editor_staff_member_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    ), include_payload=False)
    return {
        "status": "saved",
        "record_id": str(row.id),
        "revision": summary["revision"],
        "state": summary["state"],
        "warning_count": summary["warning_count"],
        "shift": row.shift,
        "updated_at": _timestamp(row.updated_at),
    }


def _incident_attention(session: Session, actor) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    cursor = None
    while len(items) < 10:
        page = list_incident_summaries(
            session,
            actor,
            filters=IncidentLibraryFilters(relationship="all"),
            limit=50,
            cursor=cursor,
        )
        for item in page.items:
            if item.progress.code == "printed_or_exported":
                continue
            items.append({
                "incident_id": str(item.incident_id),
                "incident_number": item.incident_number,
                "incident_name": item.incident_name,
                "progress": {
                    "code": item.progress.code,
                    "label": item.progress.label,
                    "blocking_count": item.progress.blocking_count,
                },
                "report_count": item.officer_report_count,
                "required_paperwork_count": item.required_paperwork_count,
                "updated_at": _timestamp(item.updated_at),
            })
            if len(items) == 10:
                break
        if len(items) == 10 or page.next_cursor is None:
            break
        cursor = page.next_cursor
    return items


def _account_conditions(session: Session) -> dict[str, int]:
    def count(*criteria) -> int:
        return int(
            session.scalar(
                select(func.count()).select_from(Account).where(*criteria)
            )
            or 0
        )

    return {
        "locked": count(Account.status == "locked"),
        "deactivated": count(Account.status == "deactivated"),
        "temporary_pin": count(Account.must_change_pin.is_(True)),
    }


def _availability(session: Session) -> dict[str, str]:
    pending = int(
        session.scalar(
            select(func.count())
            .select_from(TaskOutbox)
            .where(TaskOutbox.state == "pending")
        )
        or 0
    )
    return {
        "database": "Operational",
        "queue": "Degraded" if pending > 10_000 else "Operational",
        # No live dependency probe is available on this request path yet.  Do
        # not infer health from configuration or from a previous successful job.
        "ai": "Unavailable",
        "policy_expert": "Unavailable",
        "backup_restore": "Unavailable",
    }


def _recent_admin_activity(session: Session) -> list[dict[str, object]]:
    admin_ids = select(Account.id).where(Account.role == "admin")
    rows = session.scalars(
        select(AuditEvent)
        .where(AuditEvent.actor_account_id.in_(admin_ids))
        .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
        .limit(10)
    ).all()
    return [
        {
            "event_id": str(row.id),
            "action": row.action,
            "target_type": row.target_type,
            "target_id": str(row.target_id) if row.target_id else None,
            "result": row.result,
            "occurred_at": _timestamp(row.occurred_at),
        }
        for row in rows
    ]


def get_admin_overview(
    session: Session,
    actor,
    *,
    work_date: date,
    shift: str | None = None,
) -> AdminOverview:
    return AdminOverview(
        todays_paperwork={
            "assignment_roster": _paperwork_state(
                session,
                kind="assignment_roster",
                work_date=work_date,
                shift=shift,
            ),
            "uniform_inspection": _paperwork_state(
                session,
                kind="uniform_inspection",
                work_date=work_date,
                shift=shift,
            ),
        },
        incidents_needing_attention=_incident_attention(session, actor),
        account_conditions=_account_conditions(session),
        system_availability=_availability(session),
        recent_activity=_recent_admin_activity(session),
    )


@admin_overview_bp.get("/overview", endpoint="overview")
@require_browser_session
@require_browser_role("admin")
def overview_route():
    if set(request.args) - {"shift"} or len(request.args.getlist("shift")) > 1:
        raise ApiError(
            "validation_failed",
            "The administrator overview request is invalid.",
            status=400,
        )
    db = current_browser_session()
    actor = current_browser_actor()
    now = datetime.now(UTC)
    shift = request.args.get("shift")
    if shift is not None:
        shift = " ".join(shift.split())
        if not shift or len(shift) > 32:
            raise ApiError(
                "validation_failed",
                "The administrator overview request is invalid.",
                status=400,
            )
    try:
        require_browser_admin_elevation(db, actor=actor, now=now)
        overview = get_admin_overview(db, actor, work_date=now.date(), shift=shift)
    except AdminElevationRequired:
        raise ApiError(
            "admin_elevation_required",
            "Administrator PIN confirmation is required.",
            status=403,
        ) from None
    except PermissionError:
        raise ApiError("permission_denied", "Permission denied.", status=403) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable",
            "The administrator overview is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None

    return success({
        "todays_paperwork": overview.todays_paperwork,
        "incidents_needing_attention": overview.incidents_needing_attention,
        "account_conditions": overview.account_conditions,
        "system_availability": overview.system_availability,
        "recent_administrative_activity": overview.recent_activity,
    })
