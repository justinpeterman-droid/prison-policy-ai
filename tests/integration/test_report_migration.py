from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from backend.persistence.models.reporting import (
    IncidentRevision,
    ReportAccess,
    ReportRevision,
)


ROOT = Path(__file__).resolve().parents[2]
REPORT_TABLES = {
    "incidents",
    "incident_revisions",
    "reports",
    "report_access",
    "report_revisions",
}


def test_report_migration_upgrade_downgrade_and_reupgrade(db_engine):
    config = Config(str(ROOT / "alembic.ini"))
    command.upgrade(config, "20260812_0003")
    assert REPORT_TABLES <= set(inspect(db_engine).get_table_names())

    command.downgrade(config, "20260812_0002")
    assert REPORT_TABLES.isdisjoint(inspect(db_engine).get_table_names())

    command.upgrade(config, "20260812_0003")
    assert REPORT_TABLES <= set(inspect(db_engine).get_table_names())


def test_report_migration_has_named_constraints_and_query_indexes(db_engine):
    inspector = inspect(db_engine)
    unique_names = {
        item["name"]
        for table in ("incident_revisions", "report_revisions")
        for item in inspector.get_unique_constraints(table)
    }
    assert {
        "uq_incident_revisions_parent_number",
        "uq_report_revisions_parent_number",
    } <= unique_names
    report_indexes = {item["name"] for item in inspector.get_indexes("reports")}
    assert {"ix_reports_owner_updated", "ix_reports_preparer_updated"} <= report_indexes
    with db_engine.connect() as connection:
        triggers = (
            connection.execute(
                text("""
            SELECT tgname FROM pg_trigger
            WHERE NOT tgisinternal
              AND tgrelid IN ('incident_revisions'::regclass, 'report_revisions'::regclass)
        """)
            )
            .scalars()
            .all()
        )
    assert set(triggers) >= {
        "trg_incident_revisions_immutable",
        "trg_report_revisions_immutable",
    }


def test_duplicate_revision_and_invalid_relationship_are_rejected(
    db_session,
    fictional_incident,
    fictional_report,
    fictional_staff_and_accounts,
):
    first = (
        db_session.query(IncidentRevision)
        .filter_by(
            incident_id=fictional_incident.id,
            revision_number=1,
        )
        .one()
    )
    db_session.add(
        IncidentRevision(
            incident_id=first.incident_id,
            revision_number=first.revision_number,
            editor_account_id=first.editor_account_id,
            editor_staff_member_id=first.editor_staff_member_id,
            snapshot={"schema_version": 1},
            changed_fields={},
            reason="autosave",
            client_version="1.0.0",
            request_id="request_duplicate_revision_1",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    db_session.add(
        ReportAccess(
            report_id=fictional_report.id,
            staff_member_id=fictional_staff_and_accounts.unrelated.staff_member_id,
            relationship="viewer",
            granted_by_account_id=fictional_staff_and_accounts.admin.id,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_revision_rows_reject_update(db_session, fictional_report):
    report_id = fictional_report.id
    assert (
        db_session.query(ReportRevision)
        .filter_by(
            report_id=report_id,
            revision_number=1,
        )
        .one()
        .report_id
        == report_id
    )

    with pytest.raises(DBAPIError, match="immutable"):
        db_session.execute(
            text(
                "UPDATE report_revisions SET reason='autosave' WHERE report_id=:report_id"
            ),
            {"report_id": report_id},
        )
        db_session.flush()


def test_revision_rows_reject_delete(db_session, fictional_report):
    report_id = fictional_report.id
    assert (
        db_session.query(ReportRevision)
        .filter_by(
            report_id=report_id,
            revision_number=1,
        )
        .one()
        .report_id
        == report_id
    )

    with pytest.raises(DBAPIError, match="immutable"):
        db_session.execute(
            text("DELETE FROM report_revisions WHERE report_id=:report_id"),
            {"report_id": report_id},
        )
        db_session.flush()
