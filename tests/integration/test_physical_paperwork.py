"""PostgreSQL contracts for required physical carbon-copy paperwork."""
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select

from backend.forms.catalog import load_form_catalog, sync_form_catalog
from backend.forms.physical import (
    PhysicalPaperworkNotAllowed,
    PhysicalPaperworkNotFound,
    acknowledge_physical_paperwork,
    clear_physical_acknowledgment,
)
from backend.persistence.models.forms import (
    FormTemplate,
    IncidentPacketItem,
    PhysicalPaperworkAcknowledgment,
)
from backend.identity.browser_sessions import BrowserActor


ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "templates" / "paperwork" / "catalog.json"


def _actor(account) -> BrowserActor:
    return BrowserActor(
        account_id=account.id,
        staff_member_id=account.staff_member_id,
        session_id=account.id,
        role=account.role,
        auth_version=account.auth_version,
        must_change_pin=account.must_change_pin,
    )


def _packet_item(
    db_session,
    *,
    incident,
    account,
    template_code,
    packet_state="selected",
):
    sync_form_catalog(db_session, load_form_catalog(CATALOG_PATH))
    db_session.flush()
    template = db_session.scalar(
        select(FormTemplate).where(FormTemplate.code == template_code)
    )
    item = IncidentPacketItem(
        incident_id=incident.id,
        form_template_id=template.id,
        packet_group="required",
        packet_state=packet_state,
        source_incident_revision_number=incident.current_revision_number,
        selection_reason="Fictional physical-paperwork fixture.",
        added_by_account_id=account.id,
    )
    db_session.add(item)
    db_session.flush()
    return item


def test_acknowledgment_is_attributed_and_idempotent(
    db_session,
    fictional_incident,
    fictional_staff_and_accounts,
    identity_fixed_now,
    user_actor,
):
    item = _packet_item(
        db_session,
        incident=fictional_incident,
        account=fictional_staff_and_accounts.user,
        template_code="chain_of_custody_physical",
    )
    fixed = identity_fixed_now + timedelta(minutes=30)

    first = acknowledge_physical_paperwork(
        db_session,
        user_actor,
        packet_item_id=item.id,
        note="Official carbon-copy form completed.",
        now=fixed,
    )
    replay = acknowledge_physical_paperwork(
        db_session,
        user_actor,
        packet_item_id=item.id,
        note="A replay must not rewrite the original acknowledgment.",
        now=fixed + timedelta(minutes=5),
    )

    assert replay.acknowledgment_id == first.acknowledgment_id
    assert first.packet_item_id == item.id
    assert first.acknowledged_by_account_id == user_actor.account_id
    assert first.acknowledged_by_staff_member_id == user_actor.staff_member_id
    assert first.acknowledged_at == fixed
    assert replay.acknowledged_at == fixed
    assert replay.note == "Official carbon-copy form completed."
    assert db_session.scalar(
        select(func.count()).select_from(PhysicalPaperworkAcknowledgment)
    ) == 1

    assert clear_physical_acknowledgment(
        db_session,
        user_actor,
        packet_item_id=item.id,
    ) is True
    assert clear_physical_acknowledgment(
        db_session,
        user_actor,
        packet_item_id=item.id,
    ) is False
    assert db_session.scalar(
        select(func.count()).select_from(PhysicalPaperworkAcknowledgment)
    ) == 0


def test_digital_or_unselected_items_cannot_be_acknowledged(
    db_session,
    fictional_incident,
    fictional_staff_and_accounts,
    user_actor,
):
    digital = _packet_item(
        db_session,
        incident=fictional_incident,
        account=fictional_staff_and_accounts.user,
        template_code="form_005_409",
    )
    physical_removed = _packet_item(
        db_session,
        incident=fictional_incident,
        account=fictional_staff_and_accounts.user,
        template_code="chain_of_custody_physical",
        packet_state="removed",
    )

    with pytest.raises(
        PhysicalPaperworkNotAllowed,
        match="Only selected physical paperwork can be acknowledged",
    ):
        acknowledge_physical_paperwork(
            db_session,
            user_actor,
            packet_item_id=digital.id,
        )
    with pytest.raises(
        PhysicalPaperworkNotAllowed,
        match="Only selected physical paperwork can be acknowledged",
    ):
        acknowledge_physical_paperwork(
            db_session,
            user_actor,
            packet_item_id=physical_removed.id,
        )


def test_unrelated_officer_receives_not_found(
    db_session,
    fictional_incident,
    fictional_staff_and_accounts,
):
    item = _packet_item(
        db_session,
        incident=fictional_incident,
        account=fictional_staff_and_accounts.user,
        template_code="chain_of_custody_physical",
    )

    with pytest.raises(PhysicalPaperworkNotFound):
        acknowledge_physical_paperwork(
            db_session,
            _actor(fictional_staff_and_accounts.unrelated),
            packet_item_id=item.id,
        )
