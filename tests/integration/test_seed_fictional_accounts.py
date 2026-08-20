import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.identity.pins import verify_pin
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


def test_seed_fictional_accounts_is_idempotent_and_refreshes_credentials(db_engine):
    database_url = os.environ["TEST_DATABASE_URL"]

    seed_fictional_accounts(database_url)
    seed_fictional_accounts(database_url)

    with Session(db_engine) as session:
        staff = session.scalars(
            select(StaffMember).where(
                StaffMember.employee_number.in_(
                    [spec["employee_number"] for spec in FICTIONAL_ACCOUNTS]
                )
            )
        ).all()
        accounts = _accounts_by_employee_number(session)

        assert len(staff) == len(FICTIONAL_ACCOUNTS)
        assert len(accounts) == len(FICTIONAL_ACCOUNTS)

        for spec in FICTIONAL_ACCOUNTS:
            account = accounts[spec["employee_number"]]
            assert account.role == spec["role"]
            assert account.status == "active"
            assert account.must_change_pin is False
            assert account.failed_attempts == 0
            assert account.lock_cycle == 0
            assert account.locked_until is None
            assert account.deactivated_at is None
            assert account.auth_version == 2
            assert verify_pin(account.pin_hash, spec["pin"]) is True
