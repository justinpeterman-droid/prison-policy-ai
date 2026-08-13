"""Noninteractive Alembic migration entry point (upgrade/verify only)."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect


_ROOT = Path(__file__).resolve().parents[2]


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
            tables = inspect(connection).get_table_names()
    finally:
        engine.dispose()
    return {"status": "ok" if revision == head and "accounts" in tables else "mismatch", "revision": revision, "head": head}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Controlled database migration job")
    parser.add_argument("operation")
    args = parser.parse_args(argv)
    if args.operation not in {"upgrade", "verify"}:
        return 2
    started = time.monotonic()
    try:
        result = upgrade() if args.operation == "upgrade" else verify()
        revision = result if isinstance(result, str) else result["revision"]
        print(json.dumps({"status": "ok", "revision": revision, "duration": f"{time.monotonic()-started:.3f}"}, sort_keys=True))
        return 0
    except Exception:
        print(json.dumps({"status": "failed", "revision": "unknown", "duration": f"{time.monotonic()-started:.3f}"}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
