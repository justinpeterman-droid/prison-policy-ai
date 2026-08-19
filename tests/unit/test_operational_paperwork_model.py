from sqlalchemy import inspect

from backend.persistence.models.paperwork import (
    OperationalPaperworkRecord,
    OperationalPaperworkRevision,
)


def test_operational_paperwork_record_has_stable_daily_identity():
    table = OperationalPaperworkRecord.__table__
    columns = set(table.columns.keys())

    assert {
        "id",
        "paperwork_type",
        "record_date",
        "shift",
        "record_key",
        "created_by_account_id",
        "created_by_staff_member_id",
        "current_revision_number",
        "current_content",
        "created_at",
        "updated_at",
        "archived_at",
    } <= columns
    assert "status" not in columns

    unique_names = {
        constraint.name
        for constraint in table.constraints
        if constraint.name is not None
    }
    assert "uq_operational_paperwork_identity" in unique_names


def test_operational_paperwork_revision_is_immutable_snapshot_metadata():
    table = OperationalPaperworkRevision.__table__
    columns = set(table.columns.keys())

    assert {
        "id",
        "paperwork_record_id",
        "revision_number",
        "editor_account_id",
        "editor_staff_member_id",
        "snapshot",
        "changed_fields",
        "reason",
        "request_id",
        "client_version",
        "created_at",
    } <= columns
    assert "updated_at" not in columns

    unique_names = {
        constraint.name
        for constraint in table.constraints
        if constraint.name is not None
    }
    assert "uq_operational_paperwork_revision_number" in unique_names


def test_operational_paperwork_tables_use_expected_names():
    assert OperationalPaperworkRecord.__tablename__ == "operational_paperwork_records"
    assert OperationalPaperworkRevision.__tablename__ == "operational_paperwork_revisions"
    assert inspect(OperationalPaperworkRecord).local_table is OperationalPaperworkRecord.__table__
