from types import SimpleNamespace

import pytest

from backend.identity.accounts import (
    LastActiveAdminError,
    change_account_role_or_status,
    create_account_for_staff,
    create_staff,
)
from backend.identity.pins import verify_pin
from backend.persistence.models.identity import Account


class Audit:
    def __init__(self): self.events = []
    def append(self, _session, event): self.events.append(event)


def _actor(account, session_id):
    return SimpleNamespace(
        account_id=account.id, staff_member_id=account.staff_member_id,
        session_id=session_id, role="admin", auth_version=account.auth_version,
    )


def test_account_create_returns_pin_once_but_database_stores_only_hash(
    db_session, fictional_admin_account, fictional_admin_tokens, identity_fixed_now,
):
    actor = _actor(fictional_admin_account, fictional_admin_tokens.session_id)
    audit = Audit()
    staff = create_staff(
        db_session, actor=actor,
        payload={"employee_number": "TEST-7001", "rank": "Officer", "first_name": "Riley",
                 "last_name": "Carter", "shift": "C"},
        now=identity_fixed_now, audit_writer=audit, request_id="request-create-staff-1",
    )
    result = create_account_for_staff(
        db_session, actor=actor, staff_id=staff.id, role="user", now=identity_fixed_now,
        audit_writer=audit, request_id="request-create-account-1",
    )
    account = db_session.get(Account, result.account_id)
    assert account.pin_hash != result.temporary_pin
    assert verify_pin(account.pin_hash, result.temporary_pin)
    assert [event.action for event in audit.events].count("admin.account_created") == 1


def test_only_active_admin_cannot_demote_self(
    db_session, fictional_admin_account, fictional_admin_tokens, identity_fixed_now,
):
    actor = _actor(fictional_admin_account, fictional_admin_tokens.session_id)
    with pytest.raises(LastActiveAdminError):
        change_account_role_or_status(
            db_session, actor=actor, target_account_id=fictional_admin_account.id,
            role="user", status="active", now=identity_fixed_now,
            audit_writer=Audit(), request_id="request-last-admin-integration-1",
        )
