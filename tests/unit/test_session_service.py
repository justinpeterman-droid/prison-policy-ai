from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from backend.identity.config import IdentitySettings
from backend.identity.sessions import (
    SessionReauthenticationRequired,
    create_session,
    list_sessions,
    logout_all,
    renew_session,
    resolve_access_session,
    revoke_session,
)
from backend.identity.tokens import hash_token
from backend.persistence.models import Account, RenewalTokenHistory, StaffMember


NOW = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
SETTINGS = IdentitySettings(
    enabled=True,
    database_url="postgresql+psycopg://fictional.invalid/test",
    identity_hash_pepper="p" * 32,
    cursor_signing_key="c" * 32,
)


class FakeSession:
    def __init__(self, scalar_results=(), rows=None):
        self.scalar_results = list(scalar_results)
        self.rows = rows
        self.added = []
        self.flush_count = 0

    def add(self, value):
        if getattr(value, "id", None) is None:
            value.id = uuid4()
        self.added.append(value)

    def flush(self):
        self.flush_count += 1

    def scalar(self, _statement):
        return self.scalar_results.pop(0) if self.scalar_results else None

    def scalars(self, _statement):
        return self

    def all(self):
        return list(self.rows if self.rows is not None else self.scalar_results)

    def execute(self, _statement):
        return None


class RecordingAudit:
    def __init__(self):
        self.events = []

    def append(self, _session, event):
        self.events.append(event)
        return uuid4()


def account_fixture(*, persistent_change=False):
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
        pin_hash="encoded",
        must_change_pin=persistent_change,
        failed_attempts=0,
        lock_cycle=0,
        auth_version=3,
    )
    account.staff_member = staff
    return account


@pytest.mark.parametrize(
    "persistent,renewal_delta",
    [
        (False, timedelta(hours=12)),
        (True, timedelta(days=30)),
    ],
)
def test_session_expiries_profile_and_plaintext_boundary(persistent, renewal_delta):
    session = FakeSession()
    account = account_fixture(persistent_change=True)
    pair = create_session(
        session,
        account,
        device_id="device-fictional-0001",
        device_label="  Intake\nDesk  ",
        persistent=persistent,
        now=NOW,
        settings=SETTINGS,
    )
    stored = session.added[0]
    assert pair.access_expires_at == NOW + timedelta(minutes=15)
    assert pair.renewal_expires_at == NOW + renewal_delta
    assert pair.requires_pin_change is True
    assert pair.profile == {
        "staff_id": str(account.staff_member.id),
        "employee_number": "TEST-1001",
        "display_name": "Officer Avery Morgan",
        "rank": "Officer",
        "shift": "A",
        "role": "user",
        "status": "active",
    }
    assert stored.device_label == "Intake Desk"
    assert stored.access_token_hash == hash_token(pair.access_token)
    assert stored.renewal_token_hash == hash_token(pair.renewal_token)
    assert pair.access_token not in repr(stored.__dict__)
    assert pair.renewal_token not in repr(stored.__dict__)


def test_renewal_rotates_hashes_preserves_nonpersistent_absolute_expiry():
    account = account_fixture()
    setup = FakeSession()
    issued = create_session(
        setup,
        account,
        device_id="device-fictional-0001",
        device_label="Desk",
        persistent=False,
        now=NOW,
        settings=SETTINGS,
    )
    current = setup.added[0]
    old_renewal_hash = current.renewal_token_hash
    session = FakeSession([current, account])
    audit = RecordingAudit()
    rotated = renew_session(
        session,
        supplied_renewal_token=issued.renewal_token,
        device_id="device-fictional-0001",
        now=NOW + timedelta(hours=1),
        settings=SETTINGS,
        audit_writer=audit,
        request_id="request-renew-1",
    )
    history = next(
        value for value in session.added if isinstance(value, RenewalTokenHistory)
    )
    assert history.token_hash == old_renewal_hash
    assert current.renewal_token_hash == hash_token(rotated.renewal_token)
    assert rotated.renewal_expires_at == NOW + timedelta(hours=12)
    assert audit.events[-1].action == "auth.session_renewed"


def test_replayed_renewal_revokes_family_and_requires_reauthentication():
    account = account_fixture()
    setup = FakeSession()
    create_session(
        setup,
        account,
        device_id="device-fictional-0001",
        device_label="Desk",
        persistent=True,
        now=NOW,
        settings=SETTINGS,
    )
    current = setup.added[0]
    history = RenewalTokenHistory(
        id=uuid4(),
        session_id=current.id,
        renewal_family_id=current.renewal_family_id,
        token_hash=hash_token("historical-token"),
        rotated_at=NOW,
        expires_at=NOW + timedelta(days=30),
        reuse_detected_at=None,
    )
    session = FakeSession([None, history, current])
    audit = RecordingAudit()
    with pytest.raises(SessionReauthenticationRequired):
        renew_session(
            session,
            supplied_renewal_token="historical-token",
            device_id="device-fictional-0001",
            now=NOW + timedelta(minutes=1),
            settings=SETTINGS,
            audit_writer=audit,
            request_id="request-replay-1",
        )
    assert history.reuse_detected_at == NOW + timedelta(minutes=1)
    assert current.revoked_at == NOW + timedelta(minutes=1)
    assert current.revoke_reason == "renewal_reuse"


def test_list_sessions_returns_only_safe_summary_fields():
    account = account_fixture()
    setup = FakeSession()
    pair = create_session(
        setup,
        account,
        device_id="device-fictional-0001",
        device_label="Desk",
        persistent=True,
        now=NOW,
        settings=SETTINGS,
    )
    session = FakeSession(setup.added)
    summaries = list_sessions(
        session, account_id=account.id, current_session_id=pair.session_id
    )
    assert len(summaries) == 1 and summaries[0].current is True
    assert set(summaries[0].__dict__) == {
        "session_id",
        "device_label",
        "persistent",
        "created_at",
        "last_used_at",
        "renewal_expires_at",
        "current",
    }


def test_resolve_access_session_rejects_auth_version_mismatch():
    account = account_fixture()
    setup = FakeSession()
    pair = create_session(
        setup,
        account,
        device_id="device-fictional-0001",
        device_label="Desk",
        persistent=False,
        now=NOW,
        settings=SETTINGS,
    )
    stored = setup.added[0]
    account.auth_version += 1
    with pytest.raises(SessionReauthenticationRequired):
        resolve_access_session(
            FakeSession([stored, account]),
            access_token=pair.access_token,
            now=NOW + timedelta(minutes=1),
        )


def test_revoke_session_is_account_scoped_and_audited():
    account = account_fixture()
    setup = FakeSession()
    pair = create_session(
        setup,
        account,
        device_id="device-fictional-0001",
        device_label="Desk",
        persistent=False,
        now=NOW,
        settings=SETTINGS,
    )
    stored = setup.added[0]
    audit = RecordingAudit()
    count = revoke_session(
        FakeSession([stored, account], rows=[stored]),
        actor_account_id=account.id,
        target_session_id=pair.session_id,
        now=NOW + timedelta(minutes=1),
        audit_writer=audit,
        request_id="request-revoke-1",
    )
    assert count == 1 and stored.revoke_reason == "user_revoked"
    assert audit.events[-1].action == "auth.session_revoked"


def test_revoke_session_refuses_missing_actor_record_before_mutation():
    account = account_fixture()
    setup = FakeSession()
    create_session(
        setup,
        account,
        device_id="device-fictional-0001",
        device_label="Desk",
        persistent=False,
        now=NOW,
        settings=SETTINGS,
    )
    stored = setup.added[0]
    with pytest.raises(SessionReauthenticationRequired):
        revoke_session(
            FakeSession([stored, None], rows=[stored]),
            actor_account_id=account.id,
            target_session_id=stored.id,
            now=NOW + timedelta(minutes=1),
            audit_writer=RecordingAudit(),
            request_id="request-revoke-missing-actor",
        )
    assert stored.revoked_at is None


def test_logout_all_increments_version_and_revokes_every_live_session():
    account = account_fixture()
    setup = FakeSession()
    create_session(
        setup,
        account,
        device_id="device-fictional-0001",
        device_label="Desk",
        persistent=False,
        now=NOW,
        settings=SETTINGS,
    )
    create_session(
        setup,
        account,
        device_id="device-fictional-0002",
        device_label="Desk 2",
        persistent=False,
        now=NOW,
        settings=SETTINGS,
    )
    rows = setup.added
    audit = RecordingAudit()
    count = logout_all(
        FakeSession([account], rows=rows),
        account_id=account.id,
        now=NOW + timedelta(minutes=1),
        audit_writer=audit,
        request_id="request-logout-all-1",
    )
    assert count == 2 and account.auth_version == 4
    assert all(row.revoke_reason == "logout_all" for row in rows)
    assert audit.events[-1].details == {"session_count": 2}
