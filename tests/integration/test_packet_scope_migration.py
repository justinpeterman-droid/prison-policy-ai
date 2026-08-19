from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from backend.persistence.models.forms import FormTemplate, IncidentPacketItem
from tests.support.reporting import make_incident


ROOT = Path(__file__).resolve().parents[2]


def _packet_shape(engine):
    inspector = inspect(engine)
    columns = {
        column["name"] for column in inspector.get_columns("incident_packet_items")
    }
    indexes = {
        index["name"] for index in inspector.get_indexes("incident_packet_items")
    }
    constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("incident_packet_items")
    }
    return columns, indexes, constraints


def test_packet_officer_scope_upgrade_downgrade_and_reupgrade(db_engine):
    config = Config(str(ROOT / "alembic.ini"))

    command.downgrade(config, "20260818_0007")
    columns, indexes, constraints = _packet_shape(db_engine)
    assert "reporting_staff_member_id" not in columns
    assert "uq_incident_packet_items_incident_template" in constraints
    assert "uq_packet_items_global_template" not in indexes
    assert "uq_packet_items_officer_template" not in indexes

    command.upgrade(config, "20260819_0008")
    columns, indexes, constraints = _packet_shape(db_engine)
    assert "reporting_staff_member_id" in columns
    assert "uq_incident_packet_items_incident_template" not in constraints
    assert {
        "uq_packet_items_global_template",
        "uq_packet_items_officer_template",
    } <= indexes

    command.downgrade(config, "20260818_0007")
    columns, indexes, constraints = _packet_shape(db_engine)
    assert "reporting_staff_member_id" not in columns
    assert "uq_incident_packet_items_incident_template" in constraints

    command.upgrade(config, "head")
    columns, indexes, constraints = _packet_shape(db_engine)
    assert "reporting_staff_member_id" in columns
    assert {
        "uq_packet_items_global_template",
        "uq_packet_items_officer_template",
    } <= indexes


def test_packet_scope_downgrade_collapses_officer_duplicates_before_old_unique_key(
    db_engine,
    db_session,
    fictional_staff_and_accounts,
):
    fixed = datetime(2026, 8, 19, 16, tzinfo=UTC)
    accounts = fictional_staff_and_accounts
    incident = make_incident(db_session, accounts.user, fixed)
    template = FormTemplate(
        code="fictional_officer_scoped_form",
        name="Fictional Officer Scoped Form",
        category="incident",
        output_kind="digital_document",
        revision_label="fictional-v1",
        active=True,
        definition={},
        created_at=fixed,
        updated_at=fixed,
    )
    db_session.add(template)
    db_session.flush()
    db_session.add_all([
        IncidentPacketItem(
            incident_id=incident.id,
            form_template_id=template.id,
            reporting_staff_member_id=account.staff_member_id,
            packet_group="required",
            packet_state="selected",
            source_incident_revision_number=1,
            selection_reason="Fictional migration fixture.",
            added_by_account_id=accounts.user.id,
            created_at=fixed,
            updated_at=fixed,
        )
        for account in (accounts.user, accounts.preparer)
    ])
    db_session.commit()

    config = Config(str(ROOT / "alembic.ini"))
    command.downgrade(config, "20260818_0007")
    with db_engine.connect() as connection:
        remaining = connection.scalar(text("""
            SELECT count(*)
            FROM incident_packet_items
            WHERE incident_id = :incident_id
              AND form_template_id = :template_id
        """), {
            "incident_id": incident.id,
            "template_id": template.id,
        })
    assert remaining == 1

    command.upgrade(config, "head")
