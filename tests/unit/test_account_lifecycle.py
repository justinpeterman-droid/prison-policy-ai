from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.identity.accounts import (
    InitialAdminBootstrapRefused,
    bootstrap_first_admin,
    create_account,
)
from backend.identity.audit import (
    AuditEventInput,
    validate_actor_attribution,
    validate_details,
)


class RecordingSession:
    def __init__(self):
        self.added = []
        self.flush_count = 0
        self.scalar_results = []

    def scalar(self, _statement):
        return self.scalar_results.pop(0)

    def execute(self, _statement, _parameters=None):
        return None

    def add(self, value):
        self.added.append(value)
        value.id = value.id or uuid4()

    def flush(self):
        self.flush_count += 1


class RecordingAuditWriter:
    def __init__(self):
        self.events = []

    def append(self, _session, event):
        self.events.append(event)
        return uuid4()


def test_create_account_returns_plaintext_once_and_persists_only_hash():
    session = RecordingSession()
    audit = RecordingAuditWriter()
    staff = SimpleNamespace(id=uuid4(), employee_number="EMP-9001", is_active=True)
    session.scalar_results = [staff, None]
    now = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
    actor_account_id, actor_staff_member_id = uuid4(), uuid4()

    result = create_account(
        session,
        staff,
        "user",
        now,
        audit,
        "request-create-1",
        actor_account_id,
        actor_staff_member_id,
    )
    account = session.added[0]
    assert result.temporary_pin not in account.pin_hash
    assert not hasattr(account, "temporary_pin")
    assert account.must_change_pin is True
    assert result.expires_at == now + timedelta(hours=24)
    assert audit.events[0].actor_account_id == actor_account_id
    assert audit.events[0].details["role"] == "user"


def _event(action, actor_account_id=None, actor_staff_member_id=None):
    return AuditEventInput(
        actor_account_id,
        actor_staff_member_id,
        action,
        "success",
        "request-test",
        "account",
        None,
        {},
    )


def test_audit_actor_attribution_rules():
    validate_actor_attribution(_event("system.initial_admin_bootstrapped"))
    validate_actor_attribution(_event("auth.login_failed"))
    validate_actor_attribution(_event("admin.account_created", uuid4(), uuid4()))
    with pytest.raises(ValueError, match="actor attribution"):
        validate_actor_attribution(_event("admin.account_created"))
    with pytest.raises(ValueError, match="actor attribution"):
        validate_actor_attribution(_event("admin.account_created", uuid4(), None))
    with pytest.raises(ValueError, match="actor attribution"):
        validate_actor_attribution(_event("system.initial_admin_bootstrapped", uuid4(), uuid4()))


def test_bootstrap_audit_requires_both_safe_detail_fields():
    with pytest.raises(ValueError, match="audit details are invalid"):
        validate_details("system.initial_admin_bootstrapped", {})
    assert validate_details(
        "system.initial_admin_bootstrapped",
        {
            "operation_id": "00000000-0000-4000-8000-000000000001",
            "approval_reference_sha256": "a" * 64,
        },
    )


def test_duplicate_account_is_refused_before_temporary_pin_generation(monkeypatch):
    session = RecordingSession()
    staff = SimpleNamespace(id=uuid4(), employee_number="EMP-9001", is_active=True)
    session.scalar_results = [staff, object()]
    calls = []
    monkeypatch.setattr(
        "backend.identity.accounts.generate_temporary_pin",
        lambda _employee_number: calls.append(True) or "Z9Y8X7W6",
    )
    with pytest.raises(ValueError, match="already has an account"):
        create_account(
            session,
            staff,
            "user",
            datetime.now(UTC),
            RecordingAuditWriter(),
            "request-create-2",
            uuid4(),
            uuid4(),
        )
    assert calls == []


def test_bootstrap_creates_exact_system_audit_and_permanently_refuses_after_account():
    now = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
    staff = SimpleNamespace(id=uuid4(), employee_number="EMP-9001", is_active=True)
    operation_id = uuid4()
    session = RecordingSession()
    session.scalar_results = [0, staff]
    audit = RecordingAuditWriter()
    result = bootstrap_first_admin(
        session,
        staff_member_id=staff.id,
        now=now,
        audit_writer=audit,
        operation_id=operation_id,
        approval_reference_sha256="a" * 64,
    )
    assert result.expires_at == now + timedelta(hours=24)
    assert session.added[0].role == "admin"
    assert audit.events[-1].details == {
        "operation_id": str(operation_id),
        "approval_reference_sha256": "a" * 64,
    }

    refused = RecordingSession()
    refused.scalar_results = [1]
    with pytest.raises(InitialAdminBootstrapRefused):
        bootstrap_first_admin(
            refused,
            staff_member_id=staff.id,
            now=now,
            audit_writer=RecordingAuditWriter(),
            operation_id=uuid4(),
            approval_reference_sha256="b" * 64,
        )
    assert refused.added == []
