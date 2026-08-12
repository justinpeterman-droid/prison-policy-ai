from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from backend.identity.accounts import unlock_account, unlock_admin_account
from backend.webapp.api_v1.admin import _rehydrate_replay


def test_unlock_clears_lock_state_without_changing_pin():
    account = SimpleNamespace(id=uuid4(), pin_hash="argon-marker", status="locked",
                              failed_attempts=5, lock_cycle=3, locked_until=datetime.now(UTC))
    unlock_admin_account(account)
    assert (account.status, account.failed_attempts, account.lock_cycle, account.locked_until) == (
        "active", 0, 0, None,
    )
    assert account.pin_hash == "argon-marker"


def test_admin_unlock_invalidates_every_old_session():
    now = datetime.now(UTC)
    account = SimpleNamespace(
        id=uuid4(), pin_hash="argon-marker", status="locked", failed_attempts=5,
        lock_cycle=2, locked_until=now, auth_version=4, updated_at=now,
    )
    stored_session = SimpleNamespace(id=uuid4(), revoked_at=None, revoke_reason=None)

    class Session:
        def scalar(self, _statement): return account
        def scalars(self, _statement): return [stored_session]
        def flush(self): return None

    class Audit:
        def append(self, _session, _event): return None

    actor = SimpleNamespace(account_id=uuid4(), staff_member_id=uuid4())
    unlock_account(
        Session(), actor=actor, target_account_id=account.id, now=now,
        audit_writer=Audit(), request_id="request-unlock-1",
    )
    assert account.auth_version == 5
    assert stored_session.revoked_at == now
    assert stored_session.revoke_reason == "admin_action"


def test_minimal_idempotency_reference_rehydrates_safe_account_shape():
    account_id = uuid4()
    now = datetime.now(UTC)
    account = SimpleNamespace(
        id=account_id, staff_member_id=uuid4(), role="user", status="active",
        must_change_pin=False, created_at=now, updated_at=now,
    )

    class Session:
        def get(self, _model, identifier):
            return account if identifier == account_id else None

    data = _rehydrate_replay(
        Session(), "admin.account_unlock", {"account_id": str(account_id), "status": "active"}
    )
    assert set(data) == {
        "account_id", "staff_id", "role", "status", "must_change_pin",
        "created_at", "updated_at",
    }
