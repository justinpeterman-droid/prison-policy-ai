from datetime import UTC, datetime
from uuid import uuid4

import pytest

from backend.identity.config import IdentitySettings
from backend.identity.pins import hash_pin, verify_pin
from backend.identity.accounts import InvalidCredentials
from backend.identity.sessions import (
    SessionReauthenticationRequired,
    change_pin,
    create_session,
)
from backend.persistence.models import Account, StaffMember


NOW = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
SETTINGS = IdentitySettings(True, "postgresql+psycopg://fictional.invalid/test", "p" * 32, "c" * 32)


class FakeSession:
    def __init__(self, account, current, sessions):
        self.results = [current, account]
        self.sessions = sessions
        self.added = []

    def scalar(self, _statement):
        return self.results.pop(0)

    def scalars(self, _statement):
        return self

    def all(self):
        return self.sessions

    def add(self, value):
        if getattr(value, "id", None) is None:
            value.id = uuid4()
        self.added.append(value)

    def flush(self):
        return None


class RecordingAudit:
    def __init__(self):
        self.events = []

    def append(self, _session, event):
        self.events.append(event)
        return uuid4()


def test_pin_change_revokes_other_sessions_rotates_current_and_increments_version():
    staff = StaffMember(
        id=uuid4(),
        employee_number="TEST-1001",
        rank="Officer",
        first_name="Avery",
        last_name="Morgan",
        shift="A",
        is_active=True,
    )
    account = Account(
        id=uuid4(),
        staff_member_id=staff.id,
        role="user",
        status="active",
        pin_hash=hash_pin("Z9Y8X7"),
        must_change_pin=True,
        temporary_pin_expires_at=NOW,
        failed_attempts=0,
        lock_cycle=0,
        auth_version=1,
    )
    account.staff_member = staff
    setup = type(
        "Setup",
        (),
        {
            "added": [],
            "add": lambda self, value: (
                setattr(value, "id", getattr(value, "id", None) or uuid4()),
                self.added.append(value),
            ),
            "flush": lambda self: None,
        },
    )()
    create_session(
        setup,
        account,
        device_id="device-fictional-0001",
        device_label="Desk",
        persistent=True,
        now=NOW,
        settings=SETTINGS,
    )
    current = setup.added[-1]
    old_renewal_hash = current.renewal_token_hash
    create_session(
        setup,
        account,
        device_id="device-fictional-0002",
        device_label="Desk 2",
        persistent=True,
        now=NOW,
        settings=SETTINGS,
    )
    other = setup.added[-1]
    audit = RecordingAudit()
    session = FakeSession(account, current, [current, other])
    replacement = change_pin(
        session,
        account_id=account.id,
        current_session_id=current.id,
        current_pin="Z9Y8X7",
        new_pin="Q7W9E2",
        device_id="device-fictional-0001",
        now=NOW,
        settings=SETTINGS,
        audit_writer=audit,
        request_id="request-pin-change-1",
    )
    assert account.auth_version == 2
    assert account.must_change_pin is False
    assert account.temporary_pin_expires_at is None
    assert verify_pin(account.pin_hash, "Q7W9E2")
    assert other.revoked_at == NOW
    assert current.revoked_at is None
    assert current.auth_version == 2
    assert current.renewal_token_hash != old_renewal_hash
    assert replacement.session_id == current.id
    assert audit.events[-1].action == "auth.pin_changed"


def test_pin_change_rejects_wrong_current_pin_without_mutation():
    staff = StaffMember(
        id=uuid4(),
        employee_number="TEST-1001",
        rank="Officer",
        first_name="Avery",
        last_name="Morgan",
        shift="A",
        is_active=True,
    )
    account = Account(
        id=uuid4(),
        staff_member_id=staff.id,
        role="user",
        status="active",
        pin_hash=hash_pin("Z9Y8X7"),
        must_change_pin=False,
        failed_attempts=0,
        lock_cycle=0,
        auth_version=1,
    )
    account.staff_member = staff
    setup = type(
        "Setup",
        (),
        {
            "added": [],
            "add": lambda self, value: (
                setattr(value, "id", getattr(value, "id", None) or uuid4()),
                self.added.append(value),
            ),
            "flush": lambda self: None,
        },
    )()
    create_session(
        setup,
        account,
        device_id="device-fictional-0001",
        device_label="Desk",
        persistent=False,
        now=NOW,
        settings=SETTINGS,
    )
    current = setup.added[-1]
    audit = RecordingAudit()
    with pytest.raises(InvalidCredentials):
        change_pin(
            FakeSession(account, current, [current]),
            account_id=account.id,
            current_session_id=current.id,
            current_pin="WRONG1",
            new_pin="Q7W9E2",
            device_id="device-fictional-0001",
            now=NOW,
            settings=SETTINGS,
            audit_writer=audit,
            request_id="request-pin-change-wrong",
        )
    assert account.auth_version == 1
    assert verify_pin(account.pin_hash, "Z9Y8X7")
    assert audit.events == []


def test_pin_change_rejects_revoked_current_session():
    staff = StaffMember(
        id=uuid4(),
        employee_number="TEST-1001",
        rank="Officer",
        first_name="Avery",
        last_name="Morgan",
        shift="A",
        is_active=True,
    )
    account = Account(
        id=uuid4(),
        staff_member_id=staff.id,
        role="user",
        status="active",
        pin_hash=hash_pin("Z9Y8X7"),
        must_change_pin=False,
        failed_attempts=0,
        lock_cycle=0,
        auth_version=1,
    )
    account.staff_member = staff
    setup = type(
        "Setup",
        (),
        {
            "added": [],
            "add": lambda self, value: (
                setattr(value, "id", getattr(value, "id", None) or uuid4()),
                self.added.append(value),
            ),
            "flush": lambda self: None,
        },
    )()
    create_session(
        setup,
        account,
        device_id="device-fictional-0001",
        device_label="Desk",
        persistent=False,
        now=NOW,
        settings=SETTINGS,
    )
    current = setup.added[-1]
    current.revoked_at = NOW
    current.revoke_reason = "user_revoked"
    with pytest.raises(SessionReauthenticationRequired):
        change_pin(
            FakeSession(account, current, [current]),
            account_id=account.id,
            current_session_id=current.id,
            current_pin="Z9Y8X7",
            new_pin="Q7W9E2",
            device_id="device-fictional-0001",
            now=NOW,
            settings=SETTINGS,
            audit_writer=RecordingAudit(),
            request_id="request-pin-change-revoked",
        )
    assert account.auth_version == 1
