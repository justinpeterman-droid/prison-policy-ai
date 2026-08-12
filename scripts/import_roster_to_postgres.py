import argparse
import json
import os
from pathlib import Path

from backend.identity.config import IdentitySettings
from backend.identity.roster_import import import_roster
from backend.persistence.database import init_database, session_scope


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import the fictional seed roster into PostgreSQL.")
    parser.add_argument("--input", default="templates/staff_roster.json")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    records = payload.get("staff") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        raise ValueError("input must contain a staff list")

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    settings = IdentitySettings(enabled=True, database_url=database_url,
                                identity_hash_pepper=None, cursor_signing_key=None)
    init_database(settings)
    with session_scope() as session:
        summary = import_roster(session, records, apply=args.apply)
    print(f"source_count={summary.source_count}")
    print(f"inserted_count={summary.inserted_count}")
    print(f"existing_count={summary.existing_count}")
    print(f"applied={str(summary.applied).lower()}")
    print(f"checksum={summary.checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
