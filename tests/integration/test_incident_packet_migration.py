from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect


ROOT = Path(__file__).resolve().parents[2]
PACKET_TABLES = {
    "form_templates",
    "incident_packet_items",
    "form_instances",
    "physical_paperwork_acknowledgments",
    "document_action_events",
}


def test_incident_packet_migration_upgrade_downgrade_and_reupgrade(db_engine):
    config = Config(str(ROOT / "alembic.ini"))

    # The shared database begins at head. Move below 0007 first so this test
    # exercises 0007's own upgrade even after later packet migrations exist.
    command.downgrade(config, "20260818_0006")
    inspector = inspect(db_engine)
    assert PACKET_TABLES.isdisjoint(inspector.get_table_names())
    incident_columns = {item["name"] for item in inspector.get_columns("incidents")}
    assert {"incident_number", "incident_name"}.isdisjoint(incident_columns)

    command.upgrade(config, "20260818_0007")
    inspector = inspect(db_engine)
    assert PACKET_TABLES <= set(inspector.get_table_names())
    incident_columns = {item["name"] for item in inspector.get_columns("incidents")}
    assert {"incident_number", "incident_name"} <= incident_columns

    command.downgrade(config, "20260818_0006")
    inspector = inspect(db_engine)
    assert PACKET_TABLES.isdisjoint(inspector.get_table_names())
    incident_columns = {item["name"] for item in inspector.get_columns("incidents")}
    assert {"incident_number", "incident_name"}.isdisjoint(incident_columns)

    # Restore the session-scoped database to the complete schema for all tests
    # that run after this one.
    command.upgrade(config, "head")
    inspector = inspect(db_engine)
    assert PACKET_TABLES <= set(inspector.get_table_names())
    incident_columns = {item["name"] for item in inspector.get_columns("incidents")}
    assert {"incident_number", "incident_name"} <= incident_columns
