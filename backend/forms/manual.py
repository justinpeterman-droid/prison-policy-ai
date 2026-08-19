"""Officer edits for catalog-approved fields on populated digital form instances."""
from datetime import UTC, datetime
from math import isfinite
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.forms.population import (
    FormInstanceView,
    FormPopulationNotAllowed,
    FormPopulationNotFound,
    calculate_form_completeness,
)
from backend.persistence.models.forms import FormInstance, FormTemplate, IncidentPacketItem
from backend.reports.persistence import IncidentNotFound, get_incident


def _allowed_fields(definition: dict) -> set[str]:
    fields: set[str] = set()
    for key in ("required_fields", "review_fields", "optional_fields"):
        values = definition.get(key, [])
        if isinstance(values, list):
            fields.update(value for value in values if isinstance(value, str))
    return fields


def _clean_fields(values: object, allowed: set[str]) -> dict[str, object]:
    if not isinstance(values, dict) or len(values) > 100:
        raise FormPopulationNotAllowed("The form field update is invalid.")
    cleaned: dict[str, object] = {}
    for key, value in values.items():
        if not isinstance(key, str) or key not in allowed:
            raise FormPopulationNotAllowed("The form field update is invalid.")
        if isinstance(value, str):
            if len(value) > 5_000:
                raise FormPopulationNotAllowed("The form field update is invalid.")
            cleaned[key] = value
        elif value is None or isinstance(value, (bool, int)):
            cleaned[key] = value
        elif isinstance(value, float) and isfinite(value):
            cleaned[key] = value
        else:
            raise FormPopulationNotAllowed("The form field update is invalid.")
    return cleaned


def save_form_manual_fields(
    session: Session,
    actor,
    *,
    form_instance_id: UUID,
    manual_fields: object,
    source_incident_revision_number: int,
    now: datetime | None = None,
) -> FormInstanceView:
    row = session.execute(
        select(FormInstance, IncidentPacketItem, FormTemplate)
        .join(IncidentPacketItem, IncidentPacketItem.id == FormInstance.packet_item_id)
        .join(FormTemplate, FormTemplate.id == IncidentPacketItem.form_template_id)
        .where(FormInstance.id == form_instance_id)
        .with_for_update()
    ).one_or_none()
    if row is None:
        raise FormPopulationNotFound("Form instance not found.")
    instance, packet_item, template = row
    try:
        incident_view = get_incident(session, actor, packet_item.incident_id)
    except IncidentNotFound:
        raise FormPopulationNotFound("Form instance not found.") from None
    if (
        template.output_kind != "digital_document"
        or packet_item.packet_state != "selected"
    ):
        raise FormPopulationNotAllowed("The selected form cannot be edited.")
    current_revision = incident_view.incident.current_revision_number
    if (
        source_incident_revision_number != current_revision
        or instance.source_incident_revision_number != current_revision
        or packet_item.source_incident_revision_number != current_revision
    ):
        raise FormPopulationNotAllowed(
            "The form must be repopulated from the current saved incident revision."
        )
    allowed = _allowed_fields(template.definition or {})
    cleaned = _clean_fields(manual_fields, allowed)
    instance.manual_fields = cleaned
    completeness = calculate_form_completeness(
        required_fields=tuple((template.definition or {}).get("required_fields", [])),
        review_fields=tuple((template.definition or {}).get("review_fields", [])),
        populated_fields=dict(instance.populated_fields or {}),
        manual_fields=cleaned,
    )
    instance.completeness = completeness.state
    instance.updated_at = now or datetime.now(UTC)
    session.flush()
    return FormInstanceView(
        form_instance_id=instance.id,
        packet_item_id=packet_item.id,
        incident_id=packet_item.incident_id,
        template_code=template.code,
        template_name=template.name,
        source_incident_revision_number=instance.source_incident_revision_number,
        populated_fields=dict(instance.populated_fields or {}),
        manual_fields=dict(instance.manual_fields or {}),
        completeness=completeness,
        updated_at=instance.updated_at,
    )
