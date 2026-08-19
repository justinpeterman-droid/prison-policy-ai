"""Incident-centered administrator search and summary aggregation."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
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
from backend.persistence.models.reporting import Incident, IncidentRevision, Report
from backend.reports.incident_library import (
    ReportingOfficerSummary,
    _blocking_validation_count,
    _display_name,
    _escape_like,
    _facts_reviewed,
    _reports_reviewed,
    _search_text,
    _selected_staff_ids,
)
from backend.reports.incident_numbers import normalize_incident_number
from backend.reports.workflow_progress import WorkflowProgress, calculate_workflow_progress


_RECORDS_STATUSES = {"in_progress", "completed", "archived"}
_SELECTION_FILTER_SQL = text("""
COALESCE(
    latest_admin_incident_revision.snapshot #> '{server_metadata,reporting_staff_ids}',
    '[]'::jsonb
) ? :reporting_staff_id
""")
_SELECTED_NAME_SEARCH_SQL = text("""
EXISTS (
    SELECT 1
    FROM jsonb_array_elements_text(
        COALESCE(
            latest_admin_incident_revision.snapshot #> '{server_metadata,reporting_staff_ids}',
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


@dataclass(frozen=True)
class AdminIncidentFilters:
    q: str | None = None
    incident_number: str | None = None
    reporting_staff_id: UUID | None = None
    prepared_by_staff_id: UUID | None = None
    incident_date_from: date | None = None
    incident_date_to: date | None = None
    created_at_from: datetime | None = None
    created_at_to: datetime | None = None
    category: str | None = None
    facility: str | None = None
    location: str | None = None
    shift: str | None = None
    records_status: str | None = None
    last_editor_staff_id: UUID | None = None
    updated_at_from: datetime | None = None
    updated_at_to: datetime | None = None

    def validate(self) -> None:
        if self.records_status is not None and self.records_status not in _RECORDS_STATUSES:
            raise ValueError("records status is invalid")
        if (
            self.incident_date_from is not None
            and self.incident_date_to is not None
            and self.incident_date_from > self.incident_date_to
        ):
            raise ValueError("incident date range is invalid")
        if (
            self.created_at_from is not None
            and self.created_at_to is not None
            and self.created_at_from > self.created_at_to
        ):
            raise ValueError("created range is invalid")
        if (
            self.updated_at_from is not None
            and self.updated_at_to is not None
            and self.updated_at_from > self.updated_at_to
        ):
            raise ValueError("updated range is invalid")
        if self.incident_number is not None:
            normalize_incident_number(self.incident_number)


@dataclass(frozen=True)
class AdminStaffSummary:
    staff_id: UUID
    display_name: str


@dataclass(frozen=True)
class AdminIncidentSummary:
    incident_id: UUID
    incident_number: str | None
    incident_name: str | None
    incident_date: date | None
    category: str | None
    facility: str | None
    location: str | None
    shift: str | None
    records_status: str
    reporting_officers: tuple[ReportingOfficerSummary, ...]
    preparers: tuple[AdminStaffSummary, ...]
    last_editor: AdminStaffSummary | None
    progress: WorkflowProgress
    officer_report_count: int
    required_paperwork_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class AdminIncidentSummaryPage:
    items: tuple[AdminIncidentSummary, ...]
    next_cursor: dict[str, str] | None


def _cursor_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("admin incident cursor is invalid")
    return parsed.astimezone(UTC)


def _text_equals(column, value: str | None):
    if value is None:
        return None
    return func.lower(column) == " ".join(value.split()).lower()


def list_admin_incident_summaries(
    session: Session,
    actor,
    *,
    filters: AdminIncidentFilters | None = None,
    limit: int = 25,
    cursor: dict[str, str] | None = None,
) -> AdminIncidentSummaryPage:
    if getattr(actor, "role", None) != "admin":
        raise PermissionError("Administrator access is required.")
    if not 1 <= limit <= 50:
        raise ValueError("limit must be from 1 through 50")
    filters = filters or AdminIncidentFilters()
    filters.validate()

    latest = aliased(IncidentRevision, name="latest_admin_incident_revision")
    statement = select(
        Incident,
        latest.snapshot,
        latest.editor_staff_member_id,
    ).join(
        latest,
        and_(
            latest.incident_id == Incident.id,
            latest.revision_number == Incident.current_revision_number,
        ),
    )
    parameters: dict[str, str] = {}

    if filters.incident_number:
        statement = statement.where(
            Incident.incident_number == normalize_incident_number(filters.incident_number)
        )
    if filters.reporting_staff_id:
        parameters["reporting_staff_id"] = str(filters.reporting_staff_id)
        report_owner_match = exists(
            select(1).select_from(Report).where(
                Report.incident_id == Incident.id,
                Report.reporting_staff_member_id == filters.reporting_staff_id,
            )
        )
        statement = statement.where(or_(_SELECTION_FILTER_SQL, report_owner_match))
    if filters.prepared_by_staff_id:
        statement = statement.where(exists(
            select(1).select_from(Report).where(
                Report.incident_id == Incident.id,
                Report.prepared_by_staff_member_id == filters.prepared_by_staff_id,
            )
        ))

    search_value = _search_text(filters.q)
    if search_value:
        pattern = f"%{_escape_like(search_value)}%"
        parameters["search_pattern"] = pattern
        report_staff_match = exists(
            select(1)
            .select_from(Report)
            .join(
                StaffMember,
                or_(
                    StaffMember.id == Report.reporting_staff_member_id,
                    StaffMember.id == Report.prepared_by_staff_member_id,
                ),
            )
            .where(
                Report.incident_id == Incident.id,
                func.concat_ws(
                    " ", StaffMember.rank, StaffMember.first_name, StaffMember.last_name,
                ).ilike(pattern, escape="\\"),
            )
        )
        statement = statement.where(or_(
            Incident.incident_number.ilike(pattern, escape="\\"),
            Incident.incident_name.ilike(pattern, escape="\\"),
            _SELECTED_NAME_SEARCH_SQL,
            report_staff_match,
        ))

    for condition in (
        _text_equals(Incident.category, filters.category),
        _text_equals(Incident.facility, filters.facility),
        _text_equals(Incident.location, filters.location),
        _text_equals(Incident.shift, filters.shift),
    ):
        if condition is not None:
            statement = statement.where(condition)
    if filters.records_status:
        statement = statement.where(Incident.status == filters.records_status)
    if filters.last_editor_staff_id:
        statement = statement.where(
            latest.editor_staff_member_id == filters.last_editor_staff_id
        )
    if filters.incident_date_from:
        statement = statement.where(Incident.incident_date >= filters.incident_date_from)
    if filters.incident_date_to:
        statement = statement.where(Incident.incident_date <= filters.incident_date_to)
    if filters.created_at_from:
        statement = statement.where(Incident.created_at >= filters.created_at_from)
    if filters.created_at_to:
        statement = statement.where(Incident.created_at <= filters.created_at_to)
    if filters.updated_at_from:
        statement = statement.where(Incident.updated_at >= filters.updated_at_from)
    if filters.updated_at_to:
        statement = statement.where(Incident.updated_at <= filters.updated_at_to)

    if cursor:
        try:
            cursor_time = _cursor_timestamp(cursor["updated_at"])
            cursor_id = UUID(cursor["id"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("admin incident cursor is invalid") from None
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
        return AdminIncidentSummaryPage((), None)

    incidents = [row[0] for row in page_rows]
    snapshots = {row[0].id: row[1] for row in page_rows}
    last_editor_ids = {row[0].id: row[2] for row in page_rows}
    incident_ids = [row.id for row in incidents]

    reports_by_incident: dict[UUID, list[Report]] = defaultdict(list)
    for report in session.scalars(
        select(Report).where(Report.incident_id.in_(incident_ids))
    ).all():
        reports_by_incident[report.incident_id].append(report)

    selections = {
        incident_id: _selected_staff_ids(snapshot)
        for incident_id, snapshot in snapshots.items()
    }
    all_staff_ids: set[UUID] = set(last_editor_ids.values())
    for values in selections.values():
        all_staff_ids.update(values)
    for reports in reports_by_incident.values():
        for report in reports:
            all_staff_ids.add(report.reporting_staff_member_id)
            all_staff_ids.add(report.prepared_by_staff_member_id)
    staff_by_id = {
        staff.id: staff
        for staff in session.scalars(
            select(StaffMember).where(StaffMember.id.in_(all_staff_ids))
        ).all()
    } if all_staff_ids else {}

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
        row.packet_item_id: row
        for row in session.scalars(
            select(FormInstance).where(FormInstance.packet_item_id.in_(packet_item_ids))
        ).all()
    } if packet_item_ids else {}
    acknowledged_items = set(session.scalars(
        select(PhysicalPaperworkAcknowledgment.packet_item_id).where(
            PhysicalPaperworkAcknowledgment.packet_item_id.in_(packet_item_ids)
        )
    ).all()) if packet_item_ids else set()

    output_incidents = set(session.scalars(
        select(DocumentActionEvent.incident_id)
        .join(Incident, Incident.id == DocumentActionEvent.incident_id)
        .where(
            DocumentActionEvent.incident_id.in_(incident_ids),
            DocumentActionEvent.action.in_(("print", "download_word", "download_pdf")),
            DocumentActionEvent.incident_revision_number == Incident.current_revision_number,
        )
    ).all())
    active_job_incidents = set(session.scalars(
        select(AiJob.incident_id).where(
            AiJob.incident_id.in_(incident_ids),
            AiJob.job_type.in_(("classify", "extract", "generate")),
            AiJob.state.in_(("queued", "running")),
        )
    ).all())

    summaries: list[AdminIncidentSummary] = []
    for incident in incidents:
        reports = reports_by_incident.get(incident.id, [])
        selected_ids = selections.get(incident.id, ())
        if not selected_ids:
            selected_ids = tuple(dict.fromkeys(
                report.reporting_staff_member_id for report in reports
            ))
        reporting_officers = tuple(
            ReportingOfficerSummary(staff_id, _display_name(staff_by_id[staff_id]))
            for staff_id in selected_ids
            if staff_id in staff_by_id
        )
        preparer_ids = tuple(dict.fromkeys(
            report.prepared_by_staff_member_id for report in reports
        ))
        preparers = tuple(
            AdminStaffSummary(staff_id, _display_name(staff_by_id[staff_id]))
            for staff_id in preparer_ids
            if staff_id in staff_by_id
        )
        editor_id = last_editor_ids.get(incident.id)
        last_editor = (
            AdminStaffSummary(editor_id, _display_name(staff_by_id[editor_id]))
            if editor_id in staff_by_id else None
        )

        packet_for_incident = packet_by_incident.get(incident.id, [])
        selected_required = [
            (item, template)
            for item, template in packet_for_incident
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
        summaries.append(AdminIncidentSummary(
            incident_id=incident.id,
            incident_number=incident.incident_number,
            incident_name=incident.incident_name,
            incident_date=incident.incident_date,
            category=incident.category,
            facility=incident.facility,
            location=incident.location,
            shift=incident.shift,
            records_status=incident.status,
            reporting_officers=reporting_officers,
            preparers=preparers,
            last_editor=last_editor,
            progress=progress,
            officer_report_count=len(reports),
            required_paperwork_count=len(selected_required),
            created_at=incident.created_at,
            updated_at=incident.updated_at,
        ))

    next_cursor = None
    if len(rows) > limit:
        last = incidents[-1]
        next_cursor = {
            "updated_at": last.updated_at.astimezone(UTC).isoformat(),
            "id": str(last.id),
        }
    return AdminIncidentSummaryPage(tuple(summaries), next_cursor)
