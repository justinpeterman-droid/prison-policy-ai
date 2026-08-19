from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect


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
