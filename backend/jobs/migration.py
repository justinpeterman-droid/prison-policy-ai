"""Noninteractive Alembic migration entry point (upgrade/verify only)."""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    UniqueConstraint,
    create_engine,
    inspect,
)

from backend.persistence.base import Base
import backend.persistence.models  # noqa: F401 - registers all mapped tables


_ROOT = Path(__file__).resolve().parents[2]

_SEARCH_INDEXES = {
    "incidents": {
        "ix_incidents_extracted_facts_gin",
        "ix_incidents_incident_date",
        "ix_incidents_facility",
        "ix_incidents_location",
        "ix_incidents_shift",
    },
    "reports": {"ix_reports_created_at", "ix_reports_updated_at"},
}

# These tables are owned by reviewed migrations but do not yet have ORM models.
# Keep them in the exact schema allowlist so verification rejects unknown drift
# without incorrectly rejecting the current linear migration head.
_MIGRATION_MANAGED_TABLES = {
    "operational_paperwork",
    "operational_paperwork_revisions",
}


def _config() -> Config:
    return Config(str(_ROOT / "alembic.ini"))


def _single_head() -> str:
    heads = ScriptDirectory.from_config(_config()).get_heads()
    if len(heads) != 1:
        raise RuntimeError("migration history must have exactly one head")
    return heads[0]


def upgrade() -> str:
    """Upgrade to the single Alembic head and return its revision identifier."""
    head = _single_head()
    command.upgrade(_config(), "head")
    return head


def _constraint_contract(table) -> dict[str, object]:
    primary_key: tuple[str, ...] = ()
    unique: set[tuple[str, ...]] = set()
    foreign_keys: set[tuple[str, str, tuple[str, ...]]] = set()
    checks: dict[str, tuple[str, ...]] = {}
    for constraint in table.constraints:
        columns = tuple(sorted(column.name for column in constraint.columns))
        if isinstance(constraint, PrimaryKeyConstraint):
            primary_key = columns
        elif isinstance(constraint, UniqueConstraint):
            unique.add(columns)
        elif isinstance(constraint, ForeignKeyConstraint):
            elements = list(constraint.elements)
            foreign_keys.add((
                columns,
                elements[0].column.table.name,
                tuple(sorted(element.column.name for element in elements)),
            ))
        elif isinstance(constraint, CheckConstraint):
            checks[str(constraint.name)] = _check_signature(str(constraint.sqltext))
    return {
        "primary_key": primary_key,
        "unique": unique,
        "foreign_keys": foreign_keys,
        "checks": checks,
    }


_CHECK_CAST = re.compile(
    r"::(?:character varying|timestamp with time zone|double precision|"
    r"bigint|boolean|bytea|integer|jsonb|numeric|text|uuid)(?:\[\])?"
)


def _check_signature(sql: str) -> tuple[str, ...]:
    normalized = _CHECK_CAST.sub("", sql.lower())
    # PostgreSQL 17 renders JSONPath identifiers with optional double quotes;
    # SQLAlchemy's model text omits them. They are semantically equivalent.
    normalized = normalized.replace('"', "")
    normalized = re.sub(r"=\s*any\s*\(\s*array\s*\[", " in (", normalized)
    normalized = normalized.replace("]", ")")
    return tuple(re.findall(
        r"'(?:''|[^'])*'|!~\*|~\*|!~|->>|->|>=|<=|<>|!=|\?\||\?&|"
        r"@>|<@|~|=|>|<|-|\?|"
        r"[a-z_][a-z0-9_]*|\d+",
        normalized,
    ))


def _schema_matches(inspector) -> bool:
    actual_tables = set(inspector.get_table_names())
    expected_tables = set(Base.metadata.tables) | _MIGRATION_MANAGED_TABLES | {"alembic_version"}
    if expected_tables != actual_tables:
        return False
    for table_name, table in Base.metadata.tables.items():
        expected_columns = set(table.columns.keys())
        actual_columns = {column["name"] for column in inspector.get_columns(table_name)}
        if expected_columns != actual_columns:
            return False

        expected_indexes = {index.name for index in table.indexes if index.name}
        expected_indexes |= _SEARCH_INDEXES.get(table_name, set())
        actual_indexes = {index["name"] for index in inspector.get_indexes(table_name)}
        if not expected_indexes <= actual_indexes:
            return False

        expected = _constraint_contract(table)
        actual_primary_key = tuple(sorted(
            inspector.get_pk_constraint(table_name).get("constrained_columns") or ()
        ))
        if expected["primary_key"] != actual_primary_key:
            return False
        actual_unique_columns = {
            tuple(sorted(item.get("column_names") or ()))
            for item in inspector.get_unique_constraints(table_name)
        }
        if not expected["unique"] <= actual_unique_columns:
            return False
        actual_foreign_keys = {
            (
                tuple(sorted(item.get("constrained_columns") or ())),
                item.get("referred_table"),
                tuple(sorted(item.get("referred_columns") or ())),
            )
            for item in inspector.get_foreign_keys(table_name)
        }
        if not expected["foreign_keys"] <= actual_foreign_keys:
            return False
        actual_check_items = inspector.get_check_constraints(table_name)
        actual_checks = [
            _check_signature(item.get("sqltext") or "") for item in actual_check_items
        ]
        for name, signature in expected["checks"].items():
            if name == "ck_ai_jobs_result_reference_reports":
                candidates = [
                    (item.get("sqltext") or "").lower()
                    for item in actual_check_items
                    if (item.get("name") or "").endswith(name)
                ]
                required_fragments = (
                    "jsonb_array_length",
                    "jsonb_path_exists",
                    "report_id",
                    "revision_number",
                    "<= 20",
                )
                if not any(all(fragment in sql for fragment in required_fragments) for sql in candidates):
                    return False
            elif signature not in actual_checks:
                return False
    return True


def verify() -> dict[str, str]:
    """Return only safe migration/database compatibility state."""
    head = _single_head()
    import os
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("database unavailable")
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            revision = connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
            schema_ok = _schema_matches(inspect(connection))
    finally:
        engine.dispose()
    return {
        "status": "ok" if revision == head and schema_ok else "mismatch",
        "revision": revision,
        "head": head,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Controlled database migration job")
    parser.add_argument("operation")
    args = parser.parse_args(argv)
    if args.operation not in {"upgrade", "verify"}:
        return 2
    started = time.monotonic()
    try:
        if args.operation == "upgrade":
            revision = upgrade()
            status = "ok"
        else:
            result = verify()
            revision = result["revision"]
            status = result["status"]
        print(json.dumps({"status": status, "revision": revision, "duration": f"{time.monotonic()-started:.3f}"}, sort_keys=True))
        return 0 if status == "ok" else 1
    except Exception:
        print(json.dumps({"status": "failed", "revision": "unknown", "duration": f"{time.monotonic()-started:.3f}"}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
