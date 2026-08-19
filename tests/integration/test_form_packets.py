"""PostgreSQL contracts for deterministic incident paperwork packets."""
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import inspect, select

from backend.forms.catalog import load_form_catalog, sync_form_catalog
from backend.forms.packets import (
    PacketMutationNotAllowed,
    PacketNotFound,
    PacketRevisionConflict,
    add_additional_form,
    build_incident_packet,
    list_incident_packet,
    mark_not_applicable,
    remove_recommended_form,
)
from backend.persistence.models.forms import FormTemplate, IncidentPacketItem
from backend.persistence.models.reporting import Incident, IncidentRevision
from backend.webapp.api_v1.middleware import Actor


ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "templates" / "paperwork" / "catalog.json"
CHECKLIST = ROOT / "templates" / "incident_checklist_v2.json"


def _incident(
    session,
    *,
    owner,
    reporting_accounts,
    category="incident_no_disciplinary",
    facts=None,
    answers=None,
):
    now = datetime(2026, 8, 19, 14, tzinfo=UTC)
    incident = Incident(
        created_by_account_id=owner.id,
        created_by_staff_member_id=owner.staff_member_id,
        status="in_progress",
        current_revision_number=1,
        incident_number="2026-08-201",
        incident_name="Fictional Packet Test",
        incident_date=date(2026, 8, 19),
        facility="Fictional Unit",
        shift="A",
        location="Fictional Hall",
        category=category,
        field_notes="Fictional packet test notes.",
        classification={},
        extracted_facts=facts or {},
        gap_answers=answers or {},
        charges=[],
        validation={},
        created_at=now,
        updated_at=now,
    )
    session.add(incident)
    session.flush()
    session.add(IncidentRevision(
        incident_id=incident.id,
        revision_number=1,
        editor_account_id=owner.id,
        editor_staff_member_id=owner.staff_member_id,
        snapshot={
            "schema_version": 1,
            "incident_number": incident.incident_number,
            "incident_name": incident.incident_name,
            "incident_date": incident.incident_date.isoformat(),
            "facility": incident.facility,
            "shift": incident.shift,
            "location": incident.location,
            "category": category,
            "field_notes": incident.field_notes,
            "classification": {},
            "extracted_facts": facts or {},
            "gap_answers": answers or {},
            "charges": [],
            "validation": {},
            "warnings": [],
            "server_metadata": {
                "reporting_staff_ids": [
                    str(account.staff_member_id) for account in reporting_accounts
                ]
            },
        },
        changed_fields={"fields": ["field_notes", "category"]},
        reason="manual_save",
        client_version="1.0.0",
        request_id="request_fictional_packet_incident_create",
        created_at=now,
    ))
    session.flush()
    return incident


def _actor(account, *, role=None):
    return Actor(
        account.id,
        account.staff_member_id,
        uuid4(),
        role or account.role,
        account.auth_version,
        account.must_change_pin,
    )


def _catalog(session):
    definitions = load_form_catalog(CATALOG)
    sync_form_catalog(session, definitions, now=datetime(2026, 8, 19, 13, tzinfo=UTC))
    session.flush()


def test_packet_scope_migration_supports_multiple_officer_documents(db_engine):
    inspector = inspect(db_engine)
    columns = {column["name"] for column in inspector.get_columns("incident_packet_items")}
    indexes = {index["name"] for index in inspector.get_indexes("incident_packet_items")}

    assert "reporting_staff_member_id" in columns
    assert {
        "uq_packet_items_global_template",
        "uq_packet_items_officer_template",
    } <= indexes


def test_build_is_idempotent_and_creates_one_005_per_reporting_officer(
    db_session,
    fictional_staff_and_accounts,
):
    accounts = fictional_staff_and_accounts
    _catalog(db_session)
    incident = _incident(
        db_session,
        owner=accounts.user,
        reporting_accounts=[accounts.user, accounts.preparer],
    )
    actor = _actor(accounts.user)

    first = build_incident_packet(
        db_session,
        actor,
        incident_id=incident.id,
        incident_revision_number=1,
        checklist_path=CHECKLIST,
        now=datetime(2026, 8, 19, 14, 1, tzinfo=UTC),
    )
    db_session.flush()
    first_ids = {item.packet_item_id for item in first}
    second = build_incident_packet(
        db_session,
        actor,
        incident_id=incident.id,
        incident_revision_number=1,
        checklist_path=CHECKLIST,
        now=datetime(2026, 8, 19, 14, 2, tzinfo=UTC),
    )
    db_session.flush()

    officer_items = [item for item in second if item.template_code == "form_005_409"]
    assert {item.reporting_staff_member_id for item in officer_items} == {
        accounts.user.staff_member_id,
        accounts.preparer.staff_member_id,
    }
    assert len([item for item in second if item.template_code == "cover_letter"]) == 1
    assert {item.packet_item_id for item in second} == first_ids
    assert all(item.source_incident_revision_number == 1 for item in second)


def test_recommended_and_additional_mutations_survive_rebuild(
    db_session,
    fictional_staff_and_accounts,
):
    accounts = fictional_staff_and_accounts
    _catalog(db_session)
    incident = _incident(
        db_session,
        owner=accounts.user,
        reporting_accounts=[accounts.user],
    )
    actor = _actor(accounts.user)
    packet = build_incident_packet(
        db_session,
        actor,
        incident_id=incident.id,
        incident_revision_number=1,
        checklist_path=CHECKLIST,
    )
    photo = next(item for item in packet if item.template_code == "photo_video_attachment")
    cover = next(item for item in packet if item.template_code == "cover_letter")

    removed = remove_recommended_form(
        db_session,
        actor,
        packet_item_id=photo.packet_item_id,
        now=datetime(2026, 8, 19, 14, 3, tzinfo=UTC),
    )
    assert removed.packet_state == "removed"
    with pytest.raises(PacketMutationNotAllowed, match="recommended"):
        remove_recommended_form(
            db_session,
            actor,
            packet_item_id=cover.packet_item_id,
        )

    not_applicable = mark_not_applicable(
        db_session,
        actor,
        packet_item_id=cover.packet_item_id,
        reason="Fictional test reason approved for this scenario.",
        now=datetime(2026, 8, 19, 14, 4, tzinfo=UTC),
    )
    assert not_applicable.packet_state == "not_applicable"
    assert not_applicable.not_applicable_reason == (
        "Fictional test reason approved for this scenario."
    )

    added = add_additional_form(
        db_session,
        actor,
        incident_id=incident.id,
        incident_revision_number=1,
        template_code="additional_officer_statement",
        checklist_path=CHECKLIST,
        now=datetime(2026, 8, 19, 14, 5, tzinfo=UTC),
    )
    replay = add_additional_form(
        db_session,
        actor,
        incident_id=incident.id,
        incident_revision_number=1,
        template_code="additional_officer_statement",
        checklist_path=CHECKLIST,
        now=datetime(2026, 8, 19, 14, 6, tzinfo=UTC),
    )
    assert added.packet_item_id == replay.packet_item_id
    assert added.packet_group == "additional"

    rebuilt = build_incident_packet(
        db_session,
        actor,
        incident_id=incident.id,
        incident_revision_number=1,
        checklist_path=CHECKLIST,
        now=datetime(2026, 8, 19, 14, 7, tzinfo=UTC),
    )
    by_code = {item.template_code: item for item in rebuilt}
    assert by_code["photo_video_attachment"].packet_state == "removed"
    assert by_code["cover_letter"].packet_state == "not_applicable"
    assert by_code["additional_officer_statement"].packet_group == "additional"
    assert by_code["additional_officer_statement"].packet_state == "selected"


def test_build_refuses_stale_revision_and_unrelated_actor(
    db_session,
    fictional_staff_and_accounts,
):
    accounts = fictional_staff_and_accounts
    _catalog(db_session)
    incident = _incident(
        db_session,
        owner=accounts.user,
        reporting_accounts=[accounts.user],
    )

    with pytest.raises(PacketRevisionConflict, match="current saved incident revision"):
        build_incident_packet(
            db_session,
            _actor(accounts.user),
            incident_id=incident.id,
            incident_revision_number=2,
            checklist_path=CHECKLIST,
        )

    with pytest.raises(PacketNotFound, match="Incident not found"):
        build_incident_packet(
            db_session,
            _actor(accounts.unrelated),
            incident_id=incident.id,
            incident_revision_number=1,
            checklist_path=CHECKLIST,
        )


def test_officer_scoped_uniqueness_rejects_duplicate_same_officer(
    db_session,
    fictional_staff_and_accounts,
):
    accounts = fictional_staff_and_accounts
    _catalog(db_session)
    incident = _incident(
        db_session,
        owner=accounts.user,
        reporting_accounts=[accounts.user, accounts.preparer],
    )
    build_incident_packet(
        db_session,
        _actor(accounts.user),
        incident_id=incident.id,
        incident_revision_number=1,
        checklist_path=CHECKLIST,
    )
    db_session.flush()

    template = db_session.scalar(select(FormTemplate).where(
        FormTemplate.code == "form_005_409"
    ))
    db_session.add(IncidentPacketItem(
        incident_id=incident.id,
        form_template_id=template.id,
        reporting_staff_member_id=accounts.user.staff_member_id,
        packet_group="required",
        packet_state="selected",
        source_incident_revision_number=1,
        selection_reason="Fictional duplicate that must be rejected.",
        added_by_account_id=accounts.user.id,
    ))
    with pytest.raises(Exception):
        db_session.flush()


def test_list_packet_returns_persisted_views(
    db_session,
    fictional_staff_and_accounts,
):
    accounts = fictional_staff_and_accounts
    _catalog(db_session)
    incident = _incident(
        db_session,
        owner=accounts.user,
        reporting_accounts=[accounts.user],
    )
    actor = _actor(accounts.user)
    built = build_incident_packet(
        db_session,
        actor,
        incident_id=incident.id,
        incident_revision_number=1,
        checklist_path=CHECKLIST,
    )
    db_session.flush()

    listed = list_incident_packet(db_session, actor, incident_id=incident.id)
    assert [item.packet_item_id for item in listed] == [
        item.packet_item_id for item in built
    ]
