from backend.persistence.models.paperwork import PaperworkRecord, PaperworkRevision


PAPERWORK_KINDS = {
    "count_sheet",
    "assignment_roster",
    "uniform_inspection",
    "metal_detector_test",
    "perimeter_check",
    "random_search_log",
    "detector_sign_out",
}
REVISION_REASONS = {"autosave", "manual_save", "recovery", "restored"}


def _check_sql(table) -> str:
    return " ".join(
        str(constraint.sqltext)
        for constraint in table.constraints
        if hasattr(constraint, "sqltext")
    )


def test_paperwork_record_table_contract():
    table = PaperworkRecord.__table__

    assert table.name == "paperwork_records"
    assert {
        "id",
        "kind",
        "work_date",
        "shift",
        "current_revision_number",
        "current_payload",
        "created_by_account_id",
        "created_by_staff_member_id",
        "last_editor_account_id",
        "last_editor_staff_member_id",
        "created_at",
        "updated_at",
    } == set(table.c.keys())
    assert table.c.id.primary_key
    assert table.c.kind.nullable is False
    assert table.c.kind.type.length == 32
    assert table.c.work_date.nullable is False
    assert table.c.shift.nullable is True
    assert table.c.shift.type.length == 32
    assert table.c.current_revision_number.nullable is False
    assert table.c.current_payload.nullable is False
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False

    checks = _check_sql(table)
    assert "current_revision_number >= 1" in checks
    for value in PAPERWORK_KINDS:
        assert value in checks


def test_paperwork_record_identity_foreign_keys_are_restrictive():
    table = PaperworkRecord.__table__
    expected = {
        "created_by_account_id": "accounts.id",
        "created_by_staff_member_id": "staff_members.id",
        "last_editor_account_id": "accounts.id",
        "last_editor_staff_member_id": "staff_members.id",
    }

    for column_name, target in expected.items():
        foreign_keys = list(table.c[column_name].foreign_keys)
        assert len(foreign_keys) == 1
        assert foreign_keys[0].target_fullname == target
        assert foreign_keys[0].ondelete == "RESTRICT"


def test_paperwork_record_indexes_support_kind_owner_and_recent_queries():
    indexes = {
        index.name: tuple(column.name for column in index.columns)
        for index in PaperworkRecord.__table__.indexes
    }

    assert indexes["ix_paperwork_records_kind_date_shift"] == (
        "kind",
        "work_date",
        "shift",
        "id",
    )
    assert indexes["ix_paperwork_records_creator_updated"] == (
        "created_by_staff_member_id",
        "updated_at",
        "id",
    )
    assert indexes["ix_paperwork_records_updated"] == ("updated_at", "id")

    daily_unique = next(
        index
        for index in PaperworkRecord.__table__.indexes
        if index.name == "uq_paperwork_records_daily_date_shift"
    )
    assert daily_unique.unique is True
    assert tuple(column.name for column in daily_unique.columns) == (
        "kind",
        "work_date",
        "shift",
    )
    predicate = str(daily_unique.dialect_options["postgresql"]["where"])
    assert "count_sheet" in predicate


def test_paperwork_revision_table_contract():
    table = PaperworkRevision.__table__

    assert table.name == "paperwork_revisions"
    assert {
        "id",
        "record_id",
        "revision_number",
        "editor_account_id",
        "editor_staff_member_id",
        "snapshot",
        "changed_fields",
        "reason",
        "client_version",
        "request_id",
        "created_at",
    } == set(table.c.keys())
    assert table.c.id.primary_key
    assert table.c.record_id.nullable is False
    assert table.c.revision_number.nullable is False
    assert table.c.snapshot.nullable is False
    assert table.c.changed_fields.nullable is False
    assert table.c.reason.nullable is False
    assert table.c.client_version.nullable is False
    assert table.c.request_id.nullable is False
    assert table.c.created_at.nullable is False

    checks = _check_sql(table)
    assert "revision_number >= 1" in checks
    for value in REVISION_REASONS:
        assert value in checks


def test_paperwork_revision_parent_and_editor_contracts():
    table = PaperworkRevision.__table__
    record_fk = next(iter(table.c.record_id.foreign_keys))
    account_fk = next(iter(table.c.editor_account_id.foreign_keys))
    staff_fk = next(iter(table.c.editor_staff_member_id.foreign_keys))

    assert record_fk.target_fullname == "paperwork_records.id"
    assert record_fk.ondelete == "CASCADE"
    assert account_fk.target_fullname == "accounts.id"
    assert account_fk.ondelete == "RESTRICT"
    assert staff_fk.target_fullname == "staff_members.id"
    assert staff_fk.ondelete == "RESTRICT"

    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("record_id", "revision_number") in unique_columns

    indexes = {
        index.name: tuple(column.name for column in index.columns)
        for index in table.indexes
    }
    assert indexes["ix_paperwork_revisions_record_created"] == (
        "record_id",
        "created_at",
        "id",
    )
