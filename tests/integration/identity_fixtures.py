from datetime import datetime

from backend.identity.config import IdentitySettings
from backend.identity.pins import hash_pin
from backend.identity.sessions import SessionTokenPair, create_session
from backend.persistence.models import Account, StaffMember


TEST_IDENTITY_SETTINGS = IdentitySettings(
    enabled=True,
    database_url="postgresql+psycopg://fictional.invalid/test",
    identity_hash_pepper="p" * 32,
    cursor_signing_key="c" * 32,
)


def seed_fictional_account(
    session,
    *,
    employee_number: str,
    role: str,
    pin: str,
    now: datetime,
) -> Account:
    staff = StaffMember(
        employee_number=employee_number,
        rank="Officer",
        first_name="Avery" if role == "user" else "Jordan",
        last_name="Morgan" if role == "user" else "Taylor",
        shift="A" if role == "user" else "B",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(staff)
    session.flush()
    account = Account(
        staff_member_id=staff.id,
        role=role,
        status="active",
        pin_hash=hash_pin(pin),
        must_change_pin=False,
        failed_attempts=0,
        lock_cycle=0,
        auth_version=1,
        created_at=now,
        updated_at=now,
    )
    account.staff_member = staff
    session.add(account)
    session.flush()
    return account


def issue_fictional_tokens(
    session,
    *,
    account: Account,
    device_id: str,
    now: datetime,
) -> SessionTokenPair:
    return create_session(
        session,
        account,
        device_id=device_id,
        device_label="Fictional Test Workstation",
        persistent=False,
        now=now,
        settings=TEST_IDENTITY_SETTINGS,
    )


def bearer_headers(
    token_pair: SessionTokenPair,
    *,
    client_version: str = "1.0.0",
) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token_pair.access_token}",
        "X-Client-Version": client_version,
    }
