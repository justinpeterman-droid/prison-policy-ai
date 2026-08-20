"""Seed one deterministic fictional incident for the prod-style browser smoke.

This helper is test-only and refuses any database target that is not an
unredirectable loopback PostgreSQL URL. The standard fictional accounts must
already have been seeded by ``scripts/seed_fictional_accounts.py``.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, time
import os
from pathlib import Path
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.persistence.models.identity import Account, StaffMember
from backend.persistence.models.reporting import Incident
from scripts.seed_fictional_accounts import is_safe_local_database_url
from tests.support.reporting import make_incident, make_report


INCIDENT_ID = UUID("00000000-0000-4000-8000-00000000b001")
REPORT_ID = UUID("00000000-0000-4000-8000-00000000b002")


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "")
    if not is_safe_local_database_url(database_url):
        raise RuntimeError(
            "Refusing beta-smoke seed: DATABASE_URL must be an unredirectable "
            "loopback PostgreSQL URL."
        )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"options": "-c timezone=utc"},
    )
    try:
        fixed = datetime(2026, 8, 20, 15, 0, tzinfo=UTC)
        with Session(engine) as session, session.begin():
            account = session.scalar(
                select(Account)
                .join(StaffMember, StaffMember.id == Account.staff_member_id)
                .where(StaffMember.employee_number == "TEST-1001")
            )
            if account is None:
                raise RuntimeError("The standard fictional officer is not seeded.")
            existing = session.get(Incident, INCIDENT_ID)
            if existing is not None:
                return 0

            incident = make_incident(
                session,
                account,
                fixed,
                reporting_staff_ids=(account.staff_member_id,),
                incident_id=INCIDENT_ID,
            )
            incident.incident_number = "2026-08-901"
            incident.incident_name = "Fictional Beta Smoke Incident"
            incident.incident_date = date(2026, 8, 20)
            incident.incident_time = time(10, 15)
            incident.facility = "Fictional Training Unit"
            incident.shift = "A"
            incident.location = "Training Dayroom"
            incident.category = "fictional incident"
            incident.validation = {
                "facts_reviewed": True,
                "missing_information_reviewed": True,
            }
            make_report(
                session,
                incident=incident,
                owner=account,
                preparer=account,
                now=fixed,
                report_id=REPORT_ID,
            )
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
