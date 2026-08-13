from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.identity.accounts import (
    InvalidCredentials,
    bootstrap_first_admin,
    lock_minutes,
    record_failed_attempt,
    reset_failed_attempts,
    unlock_account,
    verify_login_pin,
    _login_account_statement,
)
from sqlalchemy.dialects import postgresql


@pytest.mark.parametrize("cycle,minutes", [(1, 15), (2, 30), (3, 60), (4, 120), (8, 1440), (20, 1440)])
def test_lock_minutes_double_with_twenty_four_hour_cap(cycle, minutes):
    assert lock_minutes(cycle) == minutes


def test_fifth_failure_locks_for_fifteen_minutes():
    now = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
    account = SimpleNamespace(failed_attempts=4, lock_cycle=0, status="active", locked_until=None)
    record_failed_attempt(account, now)
    assert account.status == "locked"
    assert account.failed_attempts == 5
    assert account.lock_cycle == 1
    assert account.locked_until == now + timedelta(minutes=15)


def test_reset_and_unlock_clear_lock_state():
    account = SimpleNamespace(failed_attempts=3, lock_cycle=4, status="locked", locked_until=datetime.now(UTC))
    unlock_account(account)
    assert (
        account.status,
        account.failed_attempts,
        account.lock_cycle,
        account.locked_until,
    ) == ("active", 0, 0, None)
    account.failed_attempts = 2
    reset_failed_attempts(account)
    assert (account.failed_attempts, account.lock_cycle) == (0, 0)


def test_bootstrap_rejects_non_hash_approval_reference_before_database_use():
    with pytest.raises(ValueError, match="approval reference SHA-256"):
        bootstrap_first_admin(
            object(),
            staff_member_id=uuid4(),
            now=datetime.now(UTC),
            audit_writer=object(),
            operation_id=uuid4(),
            approval_reference_sha256="approval-ticket-123",
        )


def test_bootstrap_rejects_non_uuid_staff_id_before_database_use():
    with pytest.raises(ValueError, match="staff member ID"):
        bootstrap_first_admin(
            object(),
            staff_member_id="not-a-uuid",
            now=datetime.now(UTC),
            audit_writer=object(),
            operation_id=uuid4(),
            approval_reference_sha256="a" * 64,
        )


def test_invalid_credentials_has_generic_shape():
    error = InvalidCredentials()
    assert str(error) == "The employee number or PIN is invalid."
    assert error.code == "invalid_credentials"


def test_unknown_invalid_employee_still_runs_one_dummy_hash(monkeypatch):
    class Session:
        def scalar(self, _statement):
            return None

    class Audit:
        def append(self, _session, _event):
            return uuid4()

    calls = []
    monkeypatch.setattr(
        "backend.identity.accounts.verify_pin",
        lambda encoded, pin: calls.append((encoded, pin)) or False,
    )
    with pytest.raises(InvalidCredentials):
        verify_login_pin(
            Session(),
            employee_number="invalid employee",
            pin="!",
            now=datetime.now(UTC),
            audit_writer=Audit(),
            request_id="request-test",
        )
    assert len(calls) == 1


def test_exact_lock_expiry_allows_success_and_resets_cycle(monkeypatch):
    now = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
    staff = SimpleNamespace(id=uuid4(), employee_number="EMP-9001", is_active=True)
    account = SimpleNamespace(
        id=uuid4(),
        staff_member_id=staff.id,
        staff_member=staff,
        status="locked",
        locked_until=now,
        failed_attempts=5,
        lock_cycle=3,
        must_change_pin=False,
        temporary_pin_expires_at=None,
        pin_hash="encoded",
        last_login_at=None,
    )

    class Session:
        def scalar(self, _statement):
            return account

    class Audit:
        def append(self, _session, _event):
            raise AssertionError("successful verification emitted failure audit")

    monkeypatch.setattr("backend.identity.accounts.verify_pin", lambda _hash, _pin: True)
    monkeypatch.setattr("backend.identity.accounts.needs_rehash", lambda _hash: False)
    result = verify_login_pin(
        Session(),
        employee_number="EMP-9001",
        pin="Z9Y8",
        now=now,
        audit_writer=Audit(),
        request_id="request-test",
    )
    assert result is account
    assert (
        account.status,
        account.failed_attempts,
        account.lock_cycle,
        account.locked_until,
        account.last_login_at,
    ) == ("active", 0, 0, None, now)


def test_current_lock_and_expired_temporary_pin_share_generic_error(monkeypatch):
    now = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
    staff = SimpleNamespace(id=uuid4(), employee_number="EMP-9001", is_active=True)

    class Session:
        def __init__(self, account):
            self.account = account

        def scalar(self, _statement):
            return self.account

    class Audit:
        def append(self, _session, _event):
            return uuid4()

    monkeypatch.setattr("backend.identity.accounts.verify_pin", lambda _hash, _pin: True)
    for account in (
        SimpleNamespace(
            id=uuid4(),
            staff_member_id=staff.id,
            staff_member=staff,
            status="locked",
            locked_until=now + timedelta(microseconds=1),
            failed_attempts=5,
            lock_cycle=1,
            must_change_pin=False,
            temporary_pin_expires_at=None,
            pin_hash="encoded",
        ),
        SimpleNamespace(
            id=uuid4(),
            staff_member_id=staff.id,
            staff_member=staff,
            status="active",
            locked_until=None,
            failed_attempts=0,
            lock_cycle=0,
            must_change_pin=True,
            temporary_pin_expires_at=now,
            pin_hash="encoded",
        ),
    ):
        with pytest.raises(InvalidCredentials) as caught:
            verify_login_pin(
                Session(account),
                employee_number="EMP-9001",
                pin="Z9Y8",
                now=now,
                audit_writer=Audit(),
                request_id="request-test",
            )
        assert str(caught.value) == "The employee number or PIN is invalid."


def test_fifth_wrong_pin_emits_failure_and_lock_events(monkeypatch):
    now = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
    staff = SimpleNamespace(id=uuid4(), employee_number="EMP-9001", is_active=True)
    account = SimpleNamespace(
        id=uuid4(),
        staff_member_id=staff.id,
        staff_member=staff,
        status="active",
        locked_until=None,
        failed_attempts=4,
        lock_cycle=0,
        must_change_pin=False,
        temporary_pin_expires_at=None,
        pin_hash="encoded",
    )

    class Session:
        def scalar(self, _statement):
            return account

    class Audit:
        def __init__(self):
            self.events = []

        def append(self, _session, event):
            self.events.append(event)
            return uuid4()

    audit = Audit()
    monkeypatch.setattr("backend.identity.accounts.verify_pin", lambda _hash, _pin: False)
    with pytest.raises(InvalidCredentials):
        verify_login_pin(
            Session(),
            employee_number="EMP-9001",
            pin="Z9Y8",
            now=now,
            audit_writer=audit,
            request_id="request-test",
        )
    assert [event.action for event in audit.events] == [
        "auth.login_failed",
        "auth.locked",
    ]
    assert audit.events[0].details == {"reason": "invalid_pin"}


def test_login_lock_query_uses_one_inner_join_and_explicit_lock_targets():
    sql = str(
        _login_account_statement("EMP-9001").compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    ).upper()
    assert sql.count("JOIN STAFF_MEMBERS") == 1
    assert "LEFT OUTER JOIN" not in sql
    assert "FOR UPDATE OF ACCOUNTS, STAFF_MEMBERS" in sql
