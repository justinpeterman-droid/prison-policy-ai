"""Authorized, incident-centered summaries for the Guided Operations library."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal, Protocol
from uuid import UUID

from sqlalchemy import and_, exists, func, or_, select, text
from sqlalchemy.orm import Session, aliased

from backend.persistence.models.forms import (
    DocumentActionEvent,
    FormInstance,
    FormTemplate,
    IncidentPacketItem,
    PhysicalPaperworkAcknowledgment,
)
from backend.persistence.models.identity import StaffMember
from backend.persistence.models.jobs import AiJob
from backend.persistence.models.reporting import (
    Incident,
    IncidentRevision,
    Report,
    ReportAccess,
)
from backend.reports.incident_numbers import normalize_incident_number
from backend.reports.workflow_progress import (
    WorkflowProgress,
    calculate_workflow_progress,
)


Relationship = Literal[
    "reporting_officer",
    "preparer",
    "both",
    "administrator",
]
RelationshipFilter = Literal["all", "reporting", "prepared"]


class IncidentLibraryActor(Protocol):
    account_id: UUID
    staff_member_id: UUID
    role: str


@dataclass(frozen=True)
class ReportingOfficerSummary:
    staff_id: UUID
    display_name: str


@dataclass(frozen=True)
class IncidentSummary:
    incident_id: UUID
    incident_number: str | None
    incident_name: str | None
    incident_date: date | None
    category: str | None
    location: str | None
    reporting_officers: tuple[ReportingOfficerSummary, ...]
    relationship: Relationship
    progress: WorkflowProgress
    officer_report_count: int
    required_paperwork_count: int
    updated_at: datetime


@dataclass(frozen=True)
class IncidentSummaryPage:
    items: tuple[IncidentSummary, ...]
    next_cursor: dict[str, str] | None


@dataclass(frozen=True)
class IncidentLibraryFilters:
    q: str | None = None
    relationship: RelationshipFilter = "all"
    category: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    location: str | None = None


_SELECTION_EXISTS_SQL = text("""
COALESCE(
    latest_incident_revision.snapshot #> '{server_metadata,reporting_staff_ids}',
    '[]'::jsonb
) ? :actor_staff_id
""")

_SELECTION_NAME_SEARCH_SQL = text("""
EXISTS (
    SELECT 1
    FROM jsonb_array_elements_text(
        COALESCE(
            latest_incident_revision.snapshot #> '{server_metadata,reporting_staff_ids}',
            '[]'::jsonb
        )
    ) AS selected_reporting_staff(staff_id)
    JOIN staff_members selected_staff
      ON selected_staff.id::text = selected_reporting_staff.staff_id
    WHERE concat_ws(
        ' ', selected_staff.rank, selected_staff.first_name, selected_staff.last_name
    ) ILIKE :search_pattern ESCAPE '\\'
)
""")


def _display_name(staff: StaffMember) -> str:
    return " ".join(
        value.strip()
        for value in (staff.rank, staff.first_name, staff.last_name)
        if value and value.strip()
    )


def _selected_staff_ids(snapshot: object) -> tuple[UUID, ...]:
    if not isinstance(snapshot, dict):
        return ()
    metadata = snapshot.get("server_metadata")
    if not isinstance(metadata, dict):
        return ()
    values = metadata.get("reporting_staff_ids")
    if not isinstance(values, list):
        return ()
    result: list[UUID] = []
    seen: set[UUID] = set()
    for value in values:
        try:
            staff_id = UUID(str(value))
        except (TypeError, ValueError):
            continue
        if staff_id not in seen:
            result.append(staff_id)
            seen.add(staff_id)
    return tuple(result)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _search_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    if not cleaned:
        return None
    compact = cleaned.replace("-", "")
    if compact.isdigit() and len(compact) == 9:
        try:
            return normalize_incident_number(cleaned)
        except ValueError:
            pass
    return cleaned


def _blocking_validation_count(validation: object) -> int:
    if not isinstance(validation, dict):
        return 0
    direct = validation.get("blocking_count")
    if isinstance(direct, int) and not isinstance(direct, bool):
        return max(0, direct)
    for key in ("blocking", "blocking_gaps", "errors"):
        value = validation.get(key)
        if isinstance(value, list):
            return len(value)
    return 0


def _facts_reviewed(incident: Incident) -> bool:
    validation = incident.validation if isinstance(incident.validation, dict) else {}
    return bool(
        validation.get("facts_reviewed")
        or validation.get("reviewed_facts")
        or validation.get("review_complete")
    )


def _reports_reviewed(reports: list[Report]) -> bool:
    if not reports:
        return False
    return all(
        report.status in {"completed", "archived"}
        or (
            isinstance(report.current_content, dict)
            and report.current_content.get("reviewed") is True
        )
        for report in reports
    )


def _relationship(
    actor: IncidentLibraryActor,
    selected_ids: tuple[UUID, ...],
    reports: list[Report],
) -> Relationship:
    reporting = actor.staff_member_id in selected_ids or any(
        report.reporting_staff_member_id == actor.staff_member_id
        for report in reports
    )
    prepared = any(
        report.prepared_by_staff_member_id == actor.staff_member_id
        for report in reports
    )
    if reporting and prepared:
        return "both"
    if reporting:
        return "reporting_officer"
    if prepared:
        return "preparer"
    if actor.role == "admin":
        return "administrator"
    # Authorization can reach legacy incidents through an owner access row even
    # when an old snapshot has no selected-officer metadata.
    return "reporting_officer"


def _cursor_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("incident cursor is invalid")
    return parsed.astimezone(UTC)


def list_incident_summaries(
    session: Session,
    actor: IncidentLibraryActor,
    *,
    filters: IncidentLibraryFilters | None = None,
    limit: int = 25,
    cursor: dict[str, str] | None = None,
) -> IncidentSummaryPage:
    """Return one authorized, aggregated row per incident in stable order."""
    if not 1 <= limit <= 50:
        raise ValueError("limit must be from 1 through 50")
    filters = filters or IncidentLibraryFilters()
    if filters.relationship not in {"all", "reporting", "prepared"}:
        raise ValueError("relationship filter is invalid")
    if filters.date_from and filters.date_to and filters.date_from > filters.date_to:
        raise ValueError("incident date range is invalid")

    latest = aliased(IncidentRevision, name="latest_incident_revision")
    statement = select(Incident, latest.snapshot).join(
        latest,
        and_(
            latest.incident_id == Incident.id,
            latest.revision_number == Incident.current_revision_number,
        ),
    )

    active_access = exists(
        select(1)
        .select_from(ReportAccess)
        .join(Report, Report.id == ReportAccess.report_id)
        .where(
            Report.incident_id == Incident.id,
            ReportAccess.staff_member_id == actor.staff_member_id,
            ReportAccess.revoked_at.is_(None),
        )
    )
    prepared_access = exists(
        select(1)
        .select_from(ReportAccess)
        .join(Report, Report.id == ReportAccess.report_id)
        .where(
            Report.incident_id == Incident.id,
            ReportAccess.staff_member_id == actor.staff_member_id,
            ReportAccess.relationship == "preparer",
            ReportAccess.revoked_at.is_(None),
        )
    )

    if actor.role != "admin":
        statement = statement.where(or_(_SELECTION_EXISTS_SQL, active_access))
    if filters.relationship == "reporting":
        statement = statement.where(_SELECTION_EXISTS_SQL)
    elif filters.relationship == "prepared":
        statement = statement.where(prepared_access)

    search_value = _search_text(filters.q)
    parameters: dict[str, str] = {"actor_staff_id": str(actor.staff_member_id)}
    if search_value:
        search_pattern = f"%{_escape_like(search_value)}%"
        parameters["search_pattern"] = search_pattern
        report_officer_name_match = exists(
            select(1)
            .select_from(Report)
            .join(
                StaffMember,
                StaffMember.id == Report.reporting_staff_member_id,
            )
            .where(
                Report.incident_id == Incident.id,
                func.concat_ws(
                    " ", StaffMember.rank, StaffMember.first_name, StaffMember.last_name,
                ).ilike(search_pattern, escape="\\"),
            )
        )
        statement = statement.where(or_(
            Incident.incident_number.ilike(search_pattern, escape="\\"),
            Incident.incident_name.ilike(search_pattern, escape="\\"),
            _SELECTION_NAME_SEARCH_SQL,
            report_officer_name_match,
        ))
    if filters.category:
        statement = statement.where(
            func.lower(Incident.category) == filters.category.strip().lower())
    if filters.location:
        statement = statement.where(
            func.lower(Incident.location) == filters.location.strip().lower())
    if filters.date_from:
        statement = statement.where(Incident.incident_date >= filters.date_from)
    if filters.date_to:
        statement = statement.where(Incident.incident_date <= filters.date_to)

    if cursor:
        try:
            cursor_time = _cursor_timestamp(cursor["created_at"])
            cursor_id = UUID(cursor["id"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("incident cursor is invalid") from None
        statement = statement.where(or_(
            Incident.updated_at < cursor_time,
            and_(Incident.updated_at == cursor_time, Incident.id < cursor_id),
        ))

    rows = session.execute(
        statement.params(**parameters)
        .order_by(Incident.updated_at.desc(), Incident.id.desc())
        .limit(limit + 1)
    ).all()
    page_rows = rows[:limit]
    if not page_rows:
        return IncidentSummaryPage((), None)

    incidents = [row[0] for row in page_rows]
    snapshots = {row[0].id: row[1] for row in page_rows}
    incident_ids = [incident.id for incident in incidents]

    reports_by_incident: dict[UUID, list[Report]] = defaultdict(list)
    for report in session.scalars(
        select(Report).where(Report.incident_id.in_(incident_ids))
    ).all():
        reports_by_incident[report.incident_id].append(report)

    selections = {
        incident_id: _selected_staff_ids(snapshot)
        for incident_id, snapshot in snapshots.items()
    }
    staff_ids = {
        staff_id
        for values in selections.values()
        for staff_id in values
    }
    if not staff_ids:
        staff_ids = {
            report.reporting_staff_member_id
            for reports in reports_by_incident.values()
            for report in reports
        }
    staff_by_id = {
        staff.id: staff
        for staff in session.scalars(
            select(StaffMember).where(StaffMember.id.in_(staff_ids))
        ).all()
    } if staff_ids else {}

    packet_rows = session.execute(
        select(IncidentPacketItem, FormTemplate)
        .join(FormTemplate, FormTemplate.id == IncidentPacketItem.form_template_id)
        .where(IncidentPacketItem.incident_id.in_(incident_ids))
    ).all()
    packet_by_incident: dict[UUID, list[tuple[IncidentPacketItem, FormTemplate]]] = defaultdict(list)
    packet_item_ids: list[UUID] = []
    for packet_item, template in packet_rows:
        packet_by_incident[packet_item.incident_id].append((packet_item, template))
        packet_item_ids.append(packet_item.id)

    instances_by_item = {
        instance.packet_item_id: instance
        for instance in session.scalars(
            select(FormInstance).where(FormInstance.packet_item_id.in_(packet_item_ids))
        ).all()
    } if packet_item_ids else {}
    acknowledged_items = set(session.scalars(
        select(PhysicalPaperworkAcknowledgment.packet_item_id).where(
            PhysicalPaperworkAcknowledgment.packet_item_id.in_(packet_item_ids)
        )
    ).all()) if packet_item_ids else set()

    output_incidents = set(session.scalars(
        select(DocumentActionEvent.incident_id).where(
            DocumentActionEvent.incident_id.in_(incident_ids),
            DocumentActionEvent.action.in_(("print", "download_word", "download_pdf")),
            DocumentActionEvent.incident_revision_number == Incident.current_revision_number,
        )
        .join(Incident, Incident.id == DocumentActionEvent.incident_id)
    ).all())
    active_job_incidents = set(session.scalars(
        select(AiJob.incident_id).where(
            AiJob.incident_id.in_(incident_ids),
            AiJob.job_type.in_(("classify", "extract", "generate")),
            AiJob.state.in_(("queued", "running")),
        )
    ).all())

    summaries: list[IncidentSummary] = []
    for incident in incidents:
        reports = reports_by_incident.get(incident.id, [])
        selected_ids = selections.get(incident.id, ())
        if not selected_ids:
            selected_ids = tuple(dict.fromkeys(
                report.reporting_staff_member_id for report in reports
            ))
        officers = tuple(
            ReportingOfficerSummary(staff_id, _display_name(staff_by_id[staff_id]))
            for staff_id in selected_ids
            if staff_id in staff_by_id
        )

        packet_rows_for_incident = packet_by_incident.get(incident.id, [])
        selected_required = [
            (item, template)
            for item, template in packet_rows_for_incident
            if item.packet_group == "required" and item.packet_state == "selected"
        ]
        required_digital = [
            item for item, template in selected_required
            if template.output_kind == "digital_document"
        ]
        required_physical = [
            item for item, template in selected_required
            if template.output_kind == "physical_only"
        ]
        digital_complete = all(
            item.id in instances_by_item
            and instances_by_item[item.id].completeness == "ready"
            for item in required_digital
        )
        missing_physical = sum(
            item.id not in acknowledged_items for item in required_physical
        )
        progress = calculate_workflow_progress(
            has_output_action=incident.id in output_incidents,
            has_active_generation_job=incident.id in active_job_incidents,
            blocking_validation_count=_blocking_validation_count(incident.validation),
            facts_reviewed=_facts_reviewed(incident),
            generated_report_count=len(reports),
            reports_reviewed=_reports_reviewed(reports),
            required_digital_forms_complete=digital_complete,
            missing_physical_acknowledgment_count=missing_physical,
            has_field_notes=bool(incident.field_notes.strip()),
        )
        summaries.append(IncidentSummary(
            incident_id=incident.id,
            incident_number=incident.incident_number,
            incident_name=incident.incident_name,
            incident_date=incident.incident_date,
            category=incident.category,
            location=incident.location,
            reporting_officers=officers,
            relationship=_relationship(actor, selected_ids, reports),
            progress=progress,
            officer_report_count=len(reports),
            required_paperwork_count=len(selected_required),
            updated_at=incident.updated_at,
        ))

    next_cursor = None
    if len(rows) > limit:
        last = incidents[-1]
        next_cursor = {
            "created_at": last.updated_at.astimezone(UTC).isoformat(),
            "id": str(last.id),
        }
    return IncidentSummaryPage(tuple(summaries), next_cursor)
