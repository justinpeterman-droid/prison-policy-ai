"""Audit contracts for carbon-copy paperwork completion and clearing."""
from datetime import timedelta
from pathlib import Path

from sqlalchemy import func, select

from backend.forms.catalog import load_form_catalog, sync_form_catalog
from backend.forms.physical import (
    acknowledge_physical_paperwork,
    clear_physical_acknowledgment,
)
from backend.persistence.models import AuditEvent
from backend.persistence.models.forms import FormTemplate, IncidentPacketItem


ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "templates" / "paperwork" / "catalog.json"


def _physical_item(db_session, incident, account):
    sync_form_catalog(db_session, load_form_catalog(CATALOG_PATH))
    db_session.flush()
    template = db_session.scalar(select(FormTemplate).where(
        FormTemplate.code == "chain_of_custody_physical"
    ))
    item = IncidentPacketItem(
        incident_id=incident.id,
        form_template_id=template.id,
        packet_group="required",
        packet_state="selected",
        source_incident_revision_number=incident.current_revision_number,
        selection_reason="Fictional physical audit fixture.",
        added_by_account_id=account.id,
    )
    db_session.add(item)
    db_session.flush()
    return item


def test_acknowledge_and_clear_append_safe_audit_events_once(
    db_session,
    fictional_incident,
    fictional_staff_and_accounts,
    identity_fixed_now,
    user_actor,
):
    item = _physical_item(
        db_session,
        fictional_incident,
        fictional_staff_and_accounts.user,
    )
    fixed = identity_fixed_now + timedelta(minutes=50)

    acknowledge_physical_paperwork(
        db_session,
        user_actor,
        packet_item_id=item.id,
        note="This note must not appear in audit details.",
        request_id="request_fictional_physical_ack",
        client_version="1.0.0",
        now=fixed,
    )
    acknowledge_physical_paperwork(
        db_session,
        user_actor,
        packet_item_id=item.id,
        note="A replay remains idempotent.",
        request_id="request_fictional_physical_ack_replay",
        client_version="1.0.0",
        now=fixed + timedelta(minutes=1),
    )
    assert clear_physical_acknowledgment(
        db_session,
        user_actor,
        packet_item_id=item.id,
        request_id="request_fictional_physical_clear",
        client_version="1.0.0",
    ) is True
    assert clear_physical_acknowledgment(
        db_session,
        user_actor,
        packet_item_id=item.id,
        request_id="request_fictional_physical_clear_replay",
        client_version="1.0.0",
    ) is False

    events = list(db_session.scalars(select(AuditEvent).where(
        AuditEvent.action.in_((
            "physical_paperwork.acknowledged",
            "physical_paperwork.cleared",
        ))
    ).order_by(AuditEvent.created_at)).all())
    assert [event.action for event in events] == [
        "physical_paperwork.acknowledged",
        "physical_paperwork.cleared",
    ]
    assert all(event.actor_account_id == user_actor.account_id for event in events)
    assert all(event.actor_staff_member_id == user_actor.staff_member_id for event in events)
    expected = {
        "incident_id": str(fictional_incident.id),
        "incident_revision_number": fictional_incident.current_revision_number,
        "packet_item_id": str(item.id),
    }
    assert events[0].details == expected
    assert events[1].details == expected
    assert "note" not in events[0].details
    assert db_session.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.action == "physical_paperwork.acknowledged"
    )) == 1
    assert db_session.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.action == "physical_paperwork.cleared"
    )) == 1
