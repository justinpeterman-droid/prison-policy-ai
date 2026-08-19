"""Migration tests must hand the schema back at head.

`db_engine` in tests/integration/conftest.py is session-scoped: it upgrades once
and every test file in the run shares that database. So whatever revision a
downgrade/re-upgrade test leaves behind becomes the schema for everything that
sorts after it.

Re-upgrading to the migration's own revision instead of "head" silently strips
every later migration for the rest of the run. That stayed invisible while newer
migrations only added new tables, and detonated the moment one added a column to
a table the ORM already selects — 14 unrelated integration tests started failing
with UndefinedColumn, in files that had nothing to do with the change.

This is a static check on purpose: it needs no database, so it runs in the fast
unit layer where a contributor sees it immediately.
"""
import ast
from pathlib import Path

import pytest


INTEGRATION = Path(__file__).resolve().parents[1] / "integration"
ALEMBIC_COMMANDS = {"upgrade", "downgrade"}


def _alembic_calls(node: ast.FunctionDef) -> list[tuple[str, str | None]]:
    """Return (command, revision) for each alembic upgrade/downgrade call."""
    calls = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Call) or not isinstance(child.func, ast.Attribute):
            continue
        if child.func.attr not in ALEMBIC_COMMANDS or len(child.args) < 2:
            continue
        revision = child.args[1]
        calls.append((
            child.func.attr,
            revision.value if isinstance(revision, ast.Constant) else None,
        ))
    return calls


def _migration_tests():
    for path in sorted(INTEGRATION.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            calls = _alembic_calls(node)
            if any(command == "downgrade" for command, _ in calls):
                yield path.name, node.name, calls


def test_there_is_something_to_check():
    """Guard against the scan silently matching nothing."""
    assert list(_migration_tests()), "no downgrade tests found — has the scan broken?"


@pytest.mark.parametrize(
    ("filename", "test_name", "calls"),
    [pytest.param(*case, id=f"{case[0]}::{case[1]}") for case in _migration_tests()],
)
def test_downgrade_tests_restore_the_schema_to_head(filename, test_name, calls):
    command, revision = calls[-1]
    assert (command, revision) == ("upgrade", "head"), (
        f"{filename}::{test_name} leaves the shared session database at "
        f"{command}({revision!r}). Finish with upgrade(config, 'head') so every "
        "test file that sorts after this one sees the full schema."
    )
