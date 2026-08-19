from pathlib import Path


MIGRATION = Path(
    "migrations/versions/20260819_0009_operational_paperwork.py"
)


def test_operational_paperwork_migration_is_linear_and_reversible():
    text = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "20260819_0009"' in text
    assert 'down_revision = "20260819_0008"' in text
    assert 'op.create_table("operational_paperwork_records"' in text
    assert 'op.create_table("operational_paperwork_revisions"' in text
    assert 'op.drop_table("operational_paperwork_revisions")' in text
    assert 'op.drop_table("operational_paperwork_records")' in text


def test_operational_paperwork_migration_identifiers_fit_postgresql():
    namespace: dict[str, object] = {}
    exec(MIGRATION.read_text(encoding="utf-8"), namespace)

    names = namespace["EXPLICIT_IDENTIFIERS"]
    assert isinstance(names, tuple)
    assert names
    assert all(isinstance(name, str) and len(name) <= 63 for name in names)
