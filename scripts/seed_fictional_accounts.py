"""Seed standard fictional local accounts for development only."""
from __future__ import annotations

import os
from pathlib import Path
import sys
from datetime import UTC, datetime
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.identity.pins import hash_pin
from backend.persistence.models import Account, StaffMember


FICTIONAL_ACCOUNTS = (
    {
        "employee_number": "TEST-1001",
        "pin": "Z9Y8X7",
        "role": "user",
        "rank": "Officer",
        "first_name": "Avery",
        "last_name": "Morgan",
        "shift": "A",
    },
    {
        "employee_number": "TEST-9001",
        "pin": "A7B8C9",
        "role": "admin",
        "rank": "Captain",
        "first_name": "Jordan",
        "last_name": "Taylor",
        "shift": "B",
    },
)


def is_safe_local_database_url(database_url: str) -> bool:
    """Return whether a URL is a loopback PostgreSQL development target."""
    if not database_url:
        return False
    parsed = urlsplit(database_url)
    is_postgres = parsed.scheme == "postgresql" or parsed.scheme.startswith(
        "postgresql+"
    )
    return (
        is_postgres
        and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        and bool(parsed.path and parsed.path != "/")
    )


def _upsert_account(session: Session, spec: dict[str, str], now: datetime) -> None:
    staff = session.scalar(
        select(StaffMember).where(StaffMember.employee_number == spec["employee_number"])
    )
    if staff is None:
        staff = StaffMember(
            employee_number=spec["employee_number"],
            rank=spec["rank"],
            first_name=spec["first_name"],
            last_name=spec["last_name"],
            shift=spec["shift"],
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(staff)
        session.flush()
    else:
        staff.rank = spec["rank"]
        staff.first_name = spec["first_name"]
        staff.last_name = spec["last_name"]
        staff.shift = spec["shift"]
        staff.is_active = True
        staff.updated_at = now

    account = session.scalar(select(Account).where(Account.staff_member_id == staff.id))
    if account is None:
        account = Account(
            staff_member_id=staff.id,
            role=spec["role"],
            status="active",
            pin_hash=hash_pin(spec["pin"]),
            must_change_pin=False,
            failed_attempts=0,
            lock_cycle=0,
            auth_version=1,
            created_at=now,
            updated_at=now,
        )
        session.add(account)
    else:
        account.role = spec["role"]
        account.status = "active"
        account.pin_hash = hash_pin(spec["pin"])
        account.must_change_pin = False
        account.temporary_pin_expires_at = None
        account.failed_attempts = 0
        account.lock_cycle = 0
        account.locked_until = None
        account.deactivated_at = None
        account.auth_version += 1
        account.updated_at = now


def seed_fictional_accounts(database_url: str) -> None:
    """Create or refresh the two standard local fictional accounts."""
    if not is_safe_local_database_url(database_url):
        raise RuntimeError(
            "Refusing to seed fictional accounts: DATABASE_URL must point to a loopback PostgreSQL database."
        )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"options": "-c timezone=utc"},
    )
    try:
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        now = datetime.now(UTC)
        with factory.begin() as session:
            for spec in FICTIONAL_ACCOUNTS:
                _upsert_account(session, spec, now)
    finally:
        engine.dispose()


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "")
    try:
        seed_fictional_accounts(database_url)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print("Seeded fictional local accounts:")
    for spec in FICTIONAL_ACCOUNTS:
        label = "Administrator" if spec["role"] == "admin" else "Officer"
        print(f"  {label}: {spec['employee_number']} / {spec['pin']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
