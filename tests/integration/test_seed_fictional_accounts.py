from datetime import UTC, datetime
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.identity.pins import hash_pin, verify_pin
from backend.persistence.models import Account, StaffMember
from scripts.seed_fictional_accounts import FICTIONAL_ACCOUNTS, seed_fictional_accounts


def _accounts_by_employee_number(session: Session) -> dict[str, Account]:
    rows = session.execute(
        select(StaffMember.employee_number, Account)
        .join(Account, Account.staff_member_id == StaffMember.id)
        .where(
            StaffMember.employee_number.in_(
                [spec["employee_number"] for spec in FICTIONAL_ACCOUNTS]
            )
        )
    ).all()
    return {employee_number: account for employee_number, account in rows}


def _staff_by_employee_number(session: Session) -> dict[str, StaffMember]:
    rows = session.scalars(
        select(StaffMember).where(
            StaffMember.employee_number.in_(
                [spec["employee_number"] for spec in FICTIONAL_ACCOUNTS]
            )
        )
    ).all()
    return {staff.employee_number: staff for staff in rows}


def test_seed_fictional_accounts_can_be_rerun_without_duplicates_and_refreshes_rows(
    db_engine,
):
    database_url = os.environ["TEST_DATABASE_URL"]
    seed_fictional_accounts(database_url)

    stale_time = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
    with Session(db_engine) as session:
        staff = _staff_by_employee_number(session)
        accounts = _accounts_by_employee_number(session)
        for spec in FICTIONAL_ACCOUNTS:
            member = staff[spec["employee_number"]]
            member.rank = "Changed"
            member.shift = "Z"
            member.is_active = False

            account = accounts[spec["employee_number"]]
            account.role = "admin" if spec["role"] == "user" else "user"
            account.status = "locked"
            account.pin_hash = hash_pin("R4T6Y8")
            account.must_change_pin = True
            account.temporary_pin_expires_at = stale_time
            account.failed_attempts = 4
            account.lock_cycle = 3
            account.locked_until = stale_time
            account.deactivated_at = stale_time
        session.commit()

    seed_fictional_accounts(database_url)

    with Session(db_engine) as session:
        staff = _staff_by_employee_number(session)
        accounts = _accounts_by_employee_number(session)

        assert len(staff) == len(FICTIONAL_ACCOUNTS)
        assert len(accounts) == len(FICTIONAL_ACCOUNTS)

        for spec in FICTIONAL_ACCOUNTS:
            member = staff[spec["employee_number"]]
            assert member.rank == spec["rank"]
            assert member.first_name == spec["first_name"]
            assert member.last_name == spec["last_name"]
            assert member.shift == spec["shift"]
            assert member.is_active is True

            account = accounts[spec["employee_number"]]
            assert account.role == spec["role"]
            assert account.status == "active"
            assert account.must_change_pin is False
            assert account.temporary_pin_expires_at is None
            assert account.failed_attempts == 0
            assert account.lock_cycle == 0
            assert account.locked_until is None
            assert account.deactivated_at is None
            assert account.auth_version == 2
            assert verify_pin(account.pin_hash, spec["pin"]) is True
