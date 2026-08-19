from sqlalchemy import inspect


def test_operational_paperwork_migration_creates_required_tables(db_engine):
    inspector = inspect(db_engine)

    assert {"paperwork_records", "paperwork_revisions"} <= set(
        inspector.get_table_names()
    )


def test_paperwork_record_migration_contract(db_engine):
    inspector = inspect(db_engine)
    columns = {
        column["name"]: column
        for column in inspector.get_columns("paperwork_records")
    }

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
    } == set(columns)
    assert columns["kind"]["nullable"] is False
    assert columns["work_date"]["nullable"] is False
    assert columns["shift"]["nullable"] is True
    assert columns["current_revision_number"]["nullable"] is False
    assert columns["current_payload"]["nullable"] is False

    indexes = {
        index["name"]: tuple(index["column_names"])
        for index in inspector.get_indexes("paperwork_records")
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

    foreign_keys = {
        tuple(foreign_key["constrained_columns"]): (
            foreign_key["referred_table"],
            foreign_key["options"].get("ondelete"),
        )
        for foreign_key in inspector.get_foreign_keys("paperwork_records")
    }
    assert foreign_keys[("created_by_account_id",)] == ("accounts", "RESTRICT")
    assert foreign_keys[("created_by_staff_member_id",)] == (
        "staff_members",
        "RESTRICT",
    )
    assert foreign_keys[("last_editor_account_id",)] == ("accounts", "RESTRICT")
    assert foreign_keys[("last_editor_staff_member_id",)] == (
        "staff_members",
        "RESTRICT",
    )


def test_paperwork_revision_migration_contract(db_engine):
    inspector = inspect(db_engine)
    columns = {
        column["name"]: column
        for column in inspector.get_columns("paperwork_revisions")
    }

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
    } == set(columns)
    assert columns["record_id"]["nullable"] is False
    assert columns["revision_number"]["nullable"] is False
    assert columns["snapshot"]["nullable"] is False
    assert columns["changed_fields"]["nullable"] is False
    assert columns["reason"]["nullable"] is False

    unique_constraints = {
        constraint["name"]: tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("paperwork_revisions")
    }
    assert unique_constraints["uq_paperwork_revisions_record_number"] == (
        "record_id",
        "revision_number",
    )

    indexes = {
        index["name"]: tuple(index["column_names"])
        for index in inspector.get_indexes("paperwork_revisions")
    }
    assert indexes["ix_paperwork_revisions_record_created"] == (
        "record_id",
        "created_at",
        "id",
    )

    foreign_keys = {
        tuple(foreign_key["constrained_columns"]): (
            foreign_key["referred_table"],
            foreign_key["options"].get("ondelete"),
        )
        for foreign_key in inspector.get_foreign_keys("paperwork_revisions")
    }
    assert foreign_keys[("record_id",)] == ("paperwork_records", "CASCADE")
    assert foreign_keys[("editor_account_id",)] == ("accounts", "RESTRICT")
    assert foreign_keys[("editor_staff_member_id",)] == (
        "staff_members",
        "RESTRICT",
    )
