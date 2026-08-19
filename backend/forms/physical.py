"""Acknowledgment service for official physical-only incident paperwork."""
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.identity.audit import (
    AuditEventInput,
    AuditWriter,
    PostgresAuditWriter,
)
from backend.persistence.models.forms import (
    FormTemplate,
    IncidentPacketItem,
    PhysicalPaperworkAcknowledgment,
)
from backend.reports.persistence import IncidentNotFound, get_incident


class PhysicalPaperworkNotFound(LookupError):
    """The paperwork item is absent or unavailable to the actor."""


class PhysicalPaperworkNotAllowed(ValueError):
    """The paperwork item cannot receive a physical completion acknowledgment."""


@dataclass(frozen=True)
class PhysicalPaperworkAcknowledgmentView:
    acknowledgment_id: UUID
    packet_item_id: UUID
    incident_id: UUID
    acknowledged_by_account_id: UUID
    acknowledged_by_staff_member_id: UUID
    note: str | None
    acknowledged_at: datetime


def _locked_item(
    session: Session,
    actor,
    packet_item_id: UUID,
) -> tuple[IncidentPacketItem, FormTemplate]:
    row = session.execute(
        select(IncidentPacketItem, FormTemplate)
        .join(FormTemplate, FormTemplate.id == IncidentPacketItem.form_template_id)
        .where(IncidentPacketItem.id == packet_item_id)
        .with_for_update()
    ).one_or_none()
    if row is None:
        raise PhysicalPaperworkNotFound("Physical paperwork item not found.")
    packet_item, template = row
    try:
        incident_view = get_incident(session, actor, packet_item.incident_id)
    except IncidentNotFound:
        raise PhysicalPaperworkNotFound(
            "Physical paperwork item not found."
        ) from None
    if (
        template.output_kind != "physical_only"
        or packet_item.packet_state != "selected"
    ):
        raise PhysicalPaperworkNotAllowed(
            "Only selected physical paperwork can be acknowledged."
        )
    if (
        packet_item.source_incident_revision_number
        != incident_view.incident.current_revision_number
    ):
        raise PhysicalPaperworkNotAllowed(
            "The physical paperwork reminder must be rebuilt for the current incident revision."
        )
    return packet_item, template


def _clean_note(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise PhysicalPaperworkNotAllowed("The acknowledgment note is invalid.")
    cleaned = " ".join(value.split())
    if len(cleaned) > 500:
        raise PhysicalPaperworkNotAllowed(
            "The acknowledgment note must be 500 characters or fewer."
        )
    return cleaned or None


def _validate_request_metadata(
    request_id: str,
    client_version: str | None,
) -> None:
    if not isinstance(request_id, str) or not 1 <= len(request_id) <= 64:
        raise PhysicalPaperworkNotAllowed(
            "The physical paperwork request ID is invalid."
        )
    if client_version is not None and (
        not isinstance(client_version, str) or len(client_version) > 64
    ):
        raise PhysicalPaperworkNotAllowed(
            "The physical paperwork client version is invalid."
        )


def _audit_details(packet_item: IncidentPacketItem) -> dict[str, object]:
    return {
        "incident_id": str(packet_item.incident_id),
        "incident_revision_number": packet_item.source_incident_revision_number,
        "packet_item_id": str(packet_item.id),
    }


def _append_audit(
    session: Session,
    actor,
    *,
    action: str,
    packet_item: IncidentPacketItem,
    request_id: str,
    client_version: str | None,
    audit_writer: AuditWriter | None,
) -> None:
    (audit_writer or PostgresAuditWriter()).append(
        session,
        AuditEventInput(
            actor_account_id=actor.account_id,
            actor_staff_member_id=actor.staff_member_id,
            action=action,
            result="success",
            request_id=request_id,
            target_type="incident_packet_item",
            target_id=packet_item.id,
            details=_audit_details(packet_item),
            client_version=client_version,
        ),
    )


def _view(
    row: PhysicalPaperworkAcknowledgment,
    incident_id: UUID,
) -> PhysicalPaperworkAcknowledgmentView:
    return PhysicalPaperworkAcknowledgmentView(
        acknowledgment_id=row.id,
        packet_item_id=row.packet_item_id,
        incident_id=incident_id,
        acknowledged_by_account_id=row.acknowledged_by_account_id,
        acknowledged_by_staff_member_id=row.acknowledged_by_staff_member_id,
        note=row.note,
        acknowledged_at=row.acknowledged_at,
    )


def acknowledge_physical_paperwork(
    session: Session,
    actor,
    *,
    packet_item_id: UUID,
    request_id: str,
    client_version: str | None,
    note: str | None = None,
    now: datetime | None = None,
    audit_writer: AuditWriter | None = None,
) -> PhysicalPaperworkAcknowledgmentView:
    """Record completion once; retries return the original attribution unchanged."""
    _validate_request_metadata(request_id, client_version)
    packet_item, _template = _locked_item(session, actor, packet_item_id)
    existing = session.scalar(
        select(PhysicalPaperworkAcknowledgment)
        .where(PhysicalPaperworkAcknowledgment.packet_item_id == packet_item.id)
        .with_for_update()
    )
    if existing is not None:
        return _view(existing, packet_item.incident_id)

    row = PhysicalPaperworkAcknowledgment(
        id=uuid4(),
        packet_item_id=packet_item.id,
        acknowledged_by_account_id=actor.account_id,
        acknowledged_by_staff_member_id=actor.staff_member_id,
        note=_clean_note(note),
        acknowledged_at=now or datetime.now(UTC),
    )
    session.add(row)
    _append_audit(
        session,
        actor,
        action="physical_paperwork.acknowledged",
        packet_item=packet_item,
        request_id=request_id,
        client_version=client_version,
        audit_writer=audit_writer,
    )
    session.flush()
    return _view(row, packet_item.incident_id)


def clear_physical_acknowledgment(
    session: Session,
    actor,
    *,
    packet_item_id: UUID,
    request_id: str,
    client_version: str | None,
    audit_writer: AuditWriter | None = None,
) -> bool:
    """Clear a current acknowledgment, returning whether a row was removed."""
    _validate_request_metadata(request_id, client_version)
    packet_item, _template = _locked_item(session, actor, packet_item_id)
    row = session.scalar(
        select(PhysicalPaperworkAcknowledgment)
        .where(PhysicalPaperworkAcknowledgment.packet_item_id == packet_item.id)
        .with_for_update()
    )
    if row is None:
        return False
    session.delete(row)
    _append_audit(
        session,
        actor,
        action="physical_paperwork.cleared",
        packet_item=packet_item,
        request_id=request_id,
        client_version=client_version,
        audit_writer=audit_writer,
    )
    session.flush()
    return True
