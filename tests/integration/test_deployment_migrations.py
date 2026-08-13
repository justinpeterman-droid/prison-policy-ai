import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from alembic.script import ScriptDirectory
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from backend.jobs import migration
from tests.support.reporting import seed_fictional_staff_and_accounts


ROOT = Path(__file__).resolve().parents[2]


def test_production_migration_runner_has_no_downgrade_subcommand():
    assert migration.main(["downgrade"]) != 0


def test_verify_cli_returns_nonzero_for_schema_mismatch(monkeypatch, capsys):
    monkeypatch.setattr(
        migration,
        "verify",
        lambda: {
            "status": "mismatch",
            "revision": "20260812_0004",
            "head": "20260812_0005",
        },
    )
    assert migration.main(["verify"]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "mismatch"
    assert output["revision"] == "20260812_0004"


def test_migration_history_is_one_linear_head():
    script = ScriptDirectory.from_config(migration._config())
    assert len(script.get_heads()) == 1
    revisions = list(script.walk_revisions())
    assert all(
        revision.down_revision is None or isinstance(revision.down_revision, str)
        for revision in revisions
    )


def test_schema_constraint_contract_is_structural_not_name_only():
    contract = migration._constraint_contract(
        migration.Base.metadata.tables["accounts"]
    )
    assert contract["primary_key"] == ("id",)
    assert ("staff_member_id",) in contract["unique"]
    assert (("staff_member_id",), "staff_members", ("id",)) in contract["foreign_keys"]
    assert set(contract["checks"]) == {
        "ck_accounts_account_role",
        "ck_accounts_account_status",
        "ck_accounts_account_failed_attempts_nonnegative",
        "ck_accounts_account_lock_cycle_nonnegative",
        "ck_accounts_account_auth_version_positive",
    }
    role_signature = contract["checks"]["ck_accounts_account_role"]
    assert migration._check_signature("role IN ('user')") != role_signature
    assert migration._check_signature(
        "failed_attempts = 0"
    ) != migration._check_signature("failed_attempts >= 0")
    assert (
        migration._check_signature(
            "role::text = ANY (ARRAY['user'::character varying, 'admin'::character varying])"
        )
        == role_signature
    )
    assert migration._check_signature(
        "error_code ~ '^[a-z]+$'"
    ) != migration._check_signature("error_code !~ '^[a-z]+$'")
    assert migration._check_signature(
        "result_reference - 'reports'"
    ) != migration._check_signature("result_reference")
    assert migration._check_signature(
        "result_reference->'reports'"
    ) != migration._check_signature("result_reference->>'reports'")


def test_verification_script_runs_from_repository_root_without_database(monkeypatch):
    environment = dict(__import__("os").environ)
    environment.pop("DATABASE_URL", None)
    result = subprocess.run(
        [sys.executable, "scripts/verify_migration.py"],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout) == {"status": "database_unavailable"}
    assert result.stderr == ""


def test_verify_checks_expected_schema_contract(db_engine):
    result = migration.verify()
    assert result == {
        "status": "ok",
        "revision": "20260812_0005",
        "head": "20260812_0005",
    }


def test_upgrade_is_idempotent_after_fictional_service_insert(
    db_session, identity_fixed_now
):
    seed_fictional_staff_and_accounts(db_session, identity_fixed_now)
    db_session.commit()
    assert migration.upgrade() == "20260812_0005"
    assert migration.upgrade() == "20260812_0005"
    inspector = inspect(db_session.get_bind())
    assert {"staff_members", "accounts", "incidents", "reports", "ai_jobs"} <= set(
        inspector.get_table_names()
    )


def test_fresh_database_exercises_only_supported_index_downgrade(
    db_engine, monkeypatch
):
    """Create a disposable DB at 0004 so no destructive revision is traversed."""
    base_url = make_url(os.environ["TEST_DATABASE_URL"])
    database_name = f"op06_lifecycle_{uuid4().hex}"
    maintenance_url = base_url.set(database="postgres")
    admin_engine = create_engine(maintenance_url, isolation_level="AUTOCOMMIT")
    isolated_url = base_url.set(database=database_name)
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{database_name}"'))
    isolated_engine = create_engine(isolated_url)
    try:
        monkeypatch.setenv(
            "DATABASE_URL", isolated_url.render_as_string(hide_password=False)
        )
        config = migration._config()
        command.upgrade(config, "20260812_0004")
        command.downgrade(config, "20260812_0003")
        with isolated_engine.connect() as connection:
            inspector = inspect(connection)
            assert {"staff_members", "accounts", "incidents", "reports"} <= set(
                inspector.get_table_names()
            )
            incident_indexes = {
                item["name"] for item in inspector.get_indexes("incidents")
            }
        assert "ix_incidents_extracted_facts_gin" not in incident_indexes
        command.upgrade(config, "20260812_0004")
        command.upgrade(config, "head")
        assert migration.verify()["status"] == "ok"
    finally:
        isolated_engine.dispose()
        with admin_engine.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :database_name AND pid <> pg_backend_pid()"
                ),
                {"database_name": database_name},
            )
            connection.execute(text(f'DROP DATABASE "{database_name}"'))
        admin_engine.dispose()
