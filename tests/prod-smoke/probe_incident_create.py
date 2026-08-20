"""Exercise the exact fictional incident-create payload before browser smoke."""
from __future__ import annotations

from datetime import date, time
import os
from pathlib import Path
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.identity.browser_sessions import BrowserActor
from backend.persistence.models.identity import Account, StaffMember
from backend.reports.persistence import create_incident
from backend.webapp.api_v1.schemas.reporting import SaveIncidentRequest
from scripts.seed_fictional_accounts import is_safe_local_database_url


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "")
    if not is_safe_local_database_url(database_url):
        raise RuntimeError("Refusing incident probe outside loopback PostgreSQL.")

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"options": "-c timezone=utc"},
    )
    try:
        with Session(engine) as session:
            account = session.scalar(
                select(Account)
                .join(StaffMember, StaffMember.id == Account.staff_member_id)
                .where(StaffMember.employee_number == "TEST-1001")
            )
            if account is None:
                raise RuntimeError("The standard fictional officer is not seeded.")
            actor = BrowserActor(
                account_id=account.id,
                staff_member_id=account.staff_member_id,
                session_id=UUID("00000000-0000-4000-8000-00000000b003"),
                role=account.role,
                auth_version=account.auth_version,
                must_change_pin=account.must_change_pin,
            )
            model = SaveIncidentRequest(
                incident_number="2026-08-902",
                incident_name="Fictional Browser Smoke Incident",
                incident_date=date(2026, 8, 20),
                incident_time=time(11, 30),
                facility="Fictional Training Unit",
                shift="A",
                location="Training Hall",
                category="fictional incident",
                field_notes=(
                    "Fictional browser-smoke observations. "
                    "Unknown details remain unknown."
                ),
            )
            create_incident(
                session,
                actor,
                [account.staff_member_id],
                model,
                "beta-smoke-direct-create-0001",
                request_id="beta-smoke-direct-create",
                client_version="0.1.0",
            )
            session.flush()
            session.rollback()
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
