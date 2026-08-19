"""Populate incident forms from saved, reviewed facts without another model call."""
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.persistence.models.forms import FormInstance, FormTemplate, IncidentPacketItem
from backend.persistence.models.identity import StaffMember
from backend.persistence.models.reporting import Report, ReportRevision, ReportType
from backend.reports.export_service import revision_metadata
from backend.reports.persistence import (
    IncidentNotFound,
    IncidentRevisionNotFound,
    get_incident,
    get_incident_revision,
)


CompletenessState = Literal["ready", "needs_review", "missing_information"]


class FormPopulationConfigurationError(ValueError):
    """A catalog field cannot be resolved by the closed population policy."""


class FormPopulationNotFound(LookupError):
    """The form instance or packet item is unavailable to the actor."""


class FormPopulationNotAllowed(ValueError):
    """The selected packet item does not support digital population."""


class FormPopulationNotReady(RuntimeError):
    """The saved incident/report state is not ready to populate a form."""


@dataclass(frozen=True)
class FormCompleteness:
    state: CompletenessState
    missing_fields: tuple[str, ...]
    review_fields: tuple[str, ...]


@dataclass(frozen=True)
class FormInstanceView:
    form_instance_id: UUID
    packet_item_id: UUID
    incident_id: UUID
    template_code: str
    template_name: str
    source_incident_revision_number: int
    populated_fields: dict[str, object]
    manual_fields: dict[str, object]
    completeness: FormCompleteness
    updated_at: datetime


@dataclass(frozen=True)
class FormPreviewView:
    form_instance_id: UUID
    packet_item_id: UUID
    incident_id: UUID
    template_code: str
    template_name: str
    render_kind: str
    fields: dict[str, object]
    completeness: FormCompleteness


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _reviewed_fact(snapshot: Mapping[str, object], key: str):
    """Prefer reviewed officer answers over extracted model suggestions."""
    for container_name in ("gap_answers", "extracted_facts", "classification"):
        container = snapshot.get(container_name)
        if isinstance(container, Mapping) and key in container:
            return container[key]
    return snapshot.get(key)


def _canonical(snapshot: Mapping[str, object], key: str):
    return snapshot.get(key)


def _injury_summary(snapshot: Mapping[str, object]):
    parts: list[str] = []
    inmate = _reviewed_fact(snapshot, "inmate_injuries")
    officer = _reviewed_fact(snapshot, "officer_injuries")
    if _has_value(inmate):
        parts.append(f"Inmate injuries: {inmate}")
    if _has_value(officer):
        parts.append(f"Officer injuries: {officer}")
    return "; ".join(parts) if parts else None


def _treatment_location(snapshot: Mapping[str, object]):
    for key in ("treatment_location", "medical_treatment_location"):
        value = _reviewed_fact(snapshot, key)
        if _has_value(value):
            return value
    return None


def _attachment_summary(snapshot: Mapping[str, object]):
    for key in (
        "attachment_summary",
        "photo_video_description",
        "attachment_description",
    ):
        value = _reviewed_fact(snapshot, key)
        if _has_value(value):
            return value
    return None


def _incident_summary(snapshot: Mapping[str, object], narrative: str | None):
    value = _reviewed_fact(snapshot, "incident_summary")
    if _has_value(value):
        return value
    return narrative if _has_value(narrative) else None


_CANONICAL_FIELDS = frozenset({
    "incident_number",
    "incident_date",
    "incident_time",
    "location",
    "category",
})
_REVIEWED_FACT_FIELDS = frozenset({
    "supervisor_name",
    "medical_disposition",
    "inmates_involved",
    "employees_involved",
    "job_code",
    "section",
    "sequence_number",
    "prea_notification_made",
    "allegation_summary",
    "evidence_description",
    "recovery_location",
    "attachment_description",
    "field_test_result_summary",
    "drug_test_disposition",
    "money_amount",
    "money_receipt_number",
    "authorization",
    "orders_given",
    "company_nurse_confirmation_number",
    "officer_injuries",
})
_CONTEXT_FIELDS = frozenset({
    "reporting_officer",
    "narrative",
    "other_involved_officers",
})
_COMPUTED_FIELDS = frozenset({
    "injury_summary",
    "treatment_location",
    "attachment_summary",
    "incident_summary",
})
_SUPPORTED_FIELDS = (
    _CANONICAL_FIELDS | _REVIEWED_FACT_FIELDS | _CONTEXT_FIELDS | _COMPUTED_FIELDS
)


def resolve_form_fields(
    snapshot: Mapping[str, object],
    field_names: Iterable[str],
    *,
    reporting_officer: str | None = None,
    narrative: str | None = None,
    other_involved_officers: Iterable[str] = (),
) -> dict[str, object]:
    """Resolve a closed set of catalog fields from one saved incident snapshot."""
    if not isinstance(snapshot, Mapping):
        raise FormPopulationConfigurationError("incident snapshot must be an object")

    resolved: dict[str, object] = {}
    officers = tuple(
        value.strip()
        for value in other_involved_officers
        if isinstance(value, str) and value.strip()
    )
    for field_name in field_names:
        if field_name not in _SUPPORTED_FIELDS:
            raise FormPopulationConfigurationError(
                f"unsupported form field: {field_name}"
            )
        if field_name in _CANONICAL_FIELDS:
            value = _canonical(snapshot, field_name)
        elif field_name in _REVIEWED_FACT_FIELDS:
            value = _reviewed_fact(snapshot, field_name)
        elif field_name == "reporting_officer":
            value = reporting_officer
        elif field_name == "narrative":
            value = narrative
        elif field_name == "other_involved_officers":
            value = list(officers) if officers else None
        elif field_name == "injury_summary":
            value = _injury_summary(snapshot)
        elif field_name == "treatment_location":
            value = _treatment_location(snapshot)
        elif field_name == "attachment_summary":
            value = _attachment_summary(snapshot)
        else:
            value = _incident_summary(snapshot, narrative)
        resolved[field_name] = value
    return resolved


def calculate_form_completeness(
    *,
    required_fields: Iterable[str],
    review_fields: Iterable[str],
    populated_fields: Mapping[str, object],
    manual_fields: Mapping[str, object] | None = None,
) -> FormCompleteness:
    """Calculate form readiness after manual values override automatic values."""
    values = dict(populated_fields)
    if manual_fields:
        values.update(manual_fields)

    required = tuple(required_fields)
    review = tuple(review_fields)
    missing = tuple(field for field in required if not _has_value(values.get(field)))
    needs_review = tuple(field for field in review if _has_value(values.get(field)))
    if missing:
        state: CompletenessState = "missing_information"
    elif needs_review:
        state = "needs_review"
    else:
        state = "ready"
    return FormCompleteness(
        state=state,
        missing_fields=missing,
        review_fields=needs_review,
    )


def _definition_fields(template: FormTemplate, key: str) -> tuple[str, ...]:
    definition = template.definition
    values = definition.get(key) if isinstance(definition, dict) else None
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise FormPopulationConfigurationError(
            f"form template {template.code} has invalid {key}"
        )
    return tuple(values)


def _facts_are_reviewed(snapshot: Mapping[str, object]) -> bool:
    validation = snapshot.get("validation")
    return isinstance(validation, Mapping) and any(
        validation.get(key) is True
        for key in (
            "facts_reviewed",
            "reviewed_facts",
            "review_complete",
            "facts_confirmed",
        )
    )


def _display_name(staff: StaffMember) -> str:
    return " ".join(
        value.strip()
        for value in (staff.rank, staff.first_name, staff.last_name)
        if value and value.strip()
    )


def _reporting_staff_ids(snapshot: Mapping[str, object]) -> tuple[UUID, ...]:
    metadata = snapshot.get("server_metadata")
    raw = metadata.get("reporting_staff_ids") if isinstance(metadata, Mapping) else None
    if not isinstance(raw, list):
        return ()
    result: list[UUID] = []
    for value in raw:
        try:
            staff_id = UUID(str(value))
        except (TypeError, ValueError):
            continue
        if staff_id not in result:
            result.append(staff_id)
    return tuple(result)


def _staff_context(
    session: Session,
    snapshot: Mapping[str, object],
    packet_item: IncidentPacketItem,
) -> tuple[StaffMember, tuple[str, ...]]:
    selected_ids = _reporting_staff_ids(snapshot)
    primary_id = packet_item.reporting_staff_member_id or (
        selected_ids[0] if selected_ids else None
    )
    if primary_id is None:
        raise FormPopulationNotReady("A reporting officer must be selected.")
    primary = session.get(StaffMember, primary_id)
    if primary is None:
        raise FormPopulationNotReady("The reporting officer is unavailable.")
    other_ids = tuple(value for value in selected_ids if value != primary_id)
    other_staff = list(session.scalars(
        select(StaffMember).where(StaffMember.id.in_(other_ids))
    ).all()) if other_ids else []
    names_by_id = {staff.id: _display_name(staff) for staff in other_staff}
    return primary, tuple(
        names_by_id[staff_id]
        for staff_id in other_ids
        if staff_id in names_by_id
    )


def _source_report(
    session: Session,
    *,
    incident_id: UUID,
    reporting_staff_member_id: UUID,
    source_report_type: str | None,
    needs_narrative: bool,
    incident_revision_id: UUID,
) -> tuple[Report | None, ReportRevision | None, str | None]:
    selected_type = source_report_type or (
        ReportType.FIRST_PERSON.value if needs_narrative else None
    )
    if selected_type is None:
        return None, None, None
    try:
        report_type = ReportType(selected_type)
    except ValueError as exc:
        raise FormPopulationConfigurationError(
            f"unsupported source report type: {selected_type}"
        ) from exc
    report = session.scalar(
        select(Report).where(
            Report.incident_id == incident_id,
            Report.report_type == report_type,
            Report.reporting_staff_member_id == reporting_staff_member_id,
        ).order_by(Report.id).limit(1)
    )
    if report is None:
        raise FormPopulationNotReady(
            f"A saved {selected_type.replace('_', ' ')} report is required."
        )
    revision = session.scalar(select(ReportRevision).where(
        ReportRevision.report_id == report.id,
        ReportRevision.revision_number == report.current_revision_number,
    ))
    if revision is None:
        raise FormPopulationNotReady("The saved source report is unavailable.")
    if revision.source_incident_revision_id != incident_revision_id:
        raise FormPopulationNotReady(
            "The saved source report must match the reviewed incident revision."
        )
    snapshot = revision.snapshot if isinstance(revision.snapshot, dict) else {}
    narrative = snapshot.get("narrative")
    return report, revision, narrative if isinstance(narrative, str) else None


def _document_date(value: object) -> str | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.strftime("%B %d, %Y")
    if isinstance(value, str):
        try:
            return date.fromisoformat(value).strftime("%B %d, %Y")
        except ValueError:
            return value.strip() or None
    return None


def _document_time(value: object) -> str | None:
    if isinstance(value, time):
        return value.strftime("%I:%M %p")
    if isinstance(value, str):
        try:
            return time.fromisoformat(value).strftime("%I:%M %p")
        except ValueError:
            return value.strip() or None
    return None


def _document_metadata(
    *,
    report: Report | None,
    revision: ReportRevision | None,
    incident_snapshot: Mapping[str, object],
    reporting_staff: StaffMember,
) -> dict[str, str] | None:
    if report is None or revision is None:
        return None
    metadata = revision_metadata(report, revision)
    metadata.setdefault("employee_number", reporting_staff.employee_number)
    metadata.setdefault("officer_first", reporting_staff.first_name or "")
    metadata.setdefault("officer_last", reporting_staff.last_name or "")
    metadata.setdefault("rank", reporting_staff.rank or "")
    metadata.setdefault(
        "shift_assignment",
        str(incident_snapshot.get("shift") or reporting_staff.shift or ""),
    )
    metadata.setdefault("unit_division", str(incident_snapshot.get("facility") or ""))
    metadata["location"] = str(incident_snapshot.get("location") or "")
    incident_date = _document_date(incident_snapshot.get("incident_date"))
    incident_time = _document_time(incident_snapshot.get("incident_time"))
    if incident_date:
        metadata["date"] = incident_date
        metadata["date_filed"] = incident_date
    if incident_time:
        metadata["time"] = incident_time
    return metadata


def _completeness(
    template: FormTemplate,
    populated_fields: Mapping[str, object],
    manual_fields: Mapping[str, object],
) -> FormCompleteness:
    return calculate_form_completeness(
        required_fields=_definition_fields(template, "required_fields"),
        review_fields=_definition_fields(template, "review_fields"),
        populated_fields=populated_fields,
        manual_fields=manual_fields,
    )


def _instance_view(
    instance: FormInstance,
    packet_item: IncidentPacketItem,
    template: FormTemplate,
) -> FormInstanceView:
    populated = dict(instance.populated_fields or {})
    manual = dict(instance.manual_fields or {})
    return FormInstanceView(
        form_instance_id=instance.id,
        packet_item_id=packet_item.id,
        incident_id=packet_item.incident_id,
        template_code=template.code,
        template_name=template.name,
        source_incident_revision_number=instance.source_incident_revision_number,
        populated_fields=populated,
        manual_fields=manual,
        completeness=_completeness(template, populated, manual),
        updated_at=instance.updated_at,
    )


def populate_form_instance(
    session: Session,
    actor,
    *,
    packet_item_id: UUID,
    incident_revision_number: int,
    now: datetime | None = None,
) -> FormInstanceView:
    """Populate one digital form from immutable reviewed incident/report revisions."""
    row = session.execute(
        select(IncidentPacketItem, FormTemplate)
        .join(FormTemplate, FormTemplate.id == IncidentPacketItem.form_template_id)
        .where(IncidentPacketItem.id == packet_item_id)
        .with_for_update()
    ).one_or_none()
    if row is None:
        raise FormPopulationNotFound("Paperwork item not found.")
    packet_item, template = row
    try:
        incident_view = get_incident(session, actor, packet_item.incident_id)
        incident_revision = get_incident_revision(
            session,
            actor,
            packet_item.incident_id,
            incident_revision_number,
        )
    except (IncidentNotFound, IncidentRevisionNotFound):
        raise FormPopulationNotFound("Paperwork item not found.") from None

    if template.output_kind != "digital_document":
        raise FormPopulationNotAllowed(
            "Physical-only paperwork cannot be digitally populated."
        )
    if packet_item.packet_state != "selected":
        raise FormPopulationNotAllowed("Only selected paperwork can be populated.")
    if packet_item.source_incident_revision_number != incident_revision_number:
        raise FormPopulationNotReady(
            "The paperwork packet must be rebuilt for this incident revision."
        )
    if incident_view.incident.current_revision_number != incident_revision_number:
        raise FormPopulationNotReady(
            "Forms can be populated only from the current saved incident revision."
        )

    snapshot = incident_revision.snapshot
    if not isinstance(snapshot, Mapping):
        raise FormPopulationConfigurationError("incident snapshot must be an object")
    if not _facts_are_reviewed(snapshot):
        raise FormPopulationNotReady(
            "Incident facts must be reviewed before forms are populated."
        )

    reporting_staff, other_officers = _staff_context(
        session, snapshot, packet_item
    )
    definition = template.definition if isinstance(template.definition, dict) else {}
    required_fields = _definition_fields(template, "required_fields")
    review_fields = _definition_fields(template, "review_fields")
    optional_fields = _definition_fields(template, "optional_fields")
    all_fields = tuple(dict.fromkeys(
        (*required_fields, *review_fields, *optional_fields)
    ))
    source_report_type = definition.get("source_report_type")
    if source_report_type is not None and not isinstance(source_report_type, str):
        raise FormPopulationConfigurationError(
            f"form template {template.code} has invalid source_report_type"
        )
    report, report_revision, narrative = _source_report(
        session,
        incident_id=packet_item.incident_id,
        reporting_staff_member_id=reporting_staff.id,
        source_report_type=source_report_type,
        needs_narrative="narrative" in all_fields,
        incident_revision_id=incident_revision.id,
    )
    populated = resolve_form_fields(
        snapshot,
        all_fields,
        reporting_officer=_display_name(reporting_staff),
        narrative=narrative,
        other_involved_officers=other_officers,
    )
    metadata = _document_metadata(
        report=report,
        revision=report_revision,
        incident_snapshot=snapshot,
        reporting_staff=reporting_staff,
    )
    if metadata is not None:
        populated["document_metadata"] = metadata

    fixed = now or datetime.now(UTC)
    instance = session.scalar(
        select(FormInstance)
        .where(FormInstance.packet_item_id == packet_item.id)
        .with_for_update()
    )
    if instance is None:
        instance = FormInstance(
            id=uuid4(),
            packet_item_id=packet_item.id,
            source_incident_revision_number=incident_revision_number,
            populated_fields=dict(populated),
            manual_fields={},
            completeness="missing_information",
            created_at=fixed,
            updated_at=fixed,
        )
        session.add(instance)
    else:
        instance.source_incident_revision_number = incident_revision_number
        instance.populated_fields = dict(populated)
        instance.updated_at = fixed

    completeness = _completeness(
        template,
        instance.populated_fields,
        instance.manual_fields,
    )
    instance.completeness = completeness.state
    session.flush()
    return _instance_view(instance, packet_item, template)


def render_form_preview(
    session: Session,
    actor,
    *,
    form_instance_id: UUID,
) -> FormPreviewView:
    """Return an authorized, structured preview without mutating the form."""
    row = session.execute(
        select(FormInstance, IncidentPacketItem, FormTemplate)
        .join(
            IncidentPacketItem,
            IncidentPacketItem.id == FormInstance.packet_item_id,
        )
        .join(FormTemplate, FormTemplate.id == IncidentPacketItem.form_template_id)
        .where(FormInstance.id == form_instance_id)
    ).one_or_none()
    if row is None:
        raise FormPopulationNotFound("Form instance not found.")
    instance, packet_item, template = row
    try:
        get_incident(session, actor, packet_item.incident_id)
    except IncidentNotFound:
        raise FormPopulationNotFound("Form instance not found.") from None
    if template.output_kind != "digital_document":
        raise FormPopulationNotAllowed(
            "Physical-only paperwork has no digital preview."
        )

    populated = dict(instance.populated_fields or {})
    manual = dict(instance.manual_fields or {})
    fields = dict(populated)
    fields.update(manual)
    definition = template.definition if isinstance(template.definition, dict) else {}
    render_kind = definition.get("render_kind")
    if not isinstance(render_kind, str):
        raise FormPopulationConfigurationError(
            f"form template {template.code} has invalid render_kind"
        )
    return FormPreviewView(
        form_instance_id=instance.id,
        packet_item_id=packet_item.id,
        incident_id=packet_item.incident_id,
        template_code=template.code,
        template_name=template.name,
        render_kind=render_kind,
        fields=fields,
        completeness=_completeness(template, populated, manual),
    )
