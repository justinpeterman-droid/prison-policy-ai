from types import SimpleNamespace

import pytest

from backend.identity.elevation import (
    StepUpRequired,
    confirm_admin_pin,
    consume_step_up,
)
from backend.persistence.models.sessions import AdminStepUpToken


class Audit:
    def __init__(self):
        self.events = []

    def append(self, _session, event):
        self.events.append(event)


def test_admin_step_up_is_hashed_session_bound_and_single_use(
    db_session,
    fictional_admin_account,
    fictional_admin_tokens,
    identity_fixed_now,
):
    actor = SimpleNamespace(
        account_id=fictional_admin_account.id,
        staff_member_id=fictional_admin_account.staff_member_id,
        session_id=fictional_admin_tokens.session_id,
        role="admin",
        auth_version=fictional_admin_account.auth_version,
    )
    audit = Audit()
    result = confirm_admin_pin(
        db_session,
        actor=actor,
        pin="Q7W9E2",
        purpose="account_reset_pin",
        now=identity_fixed_now,
        audit_writer=audit,
        request_id="request-admin-step-up-1",
    )
    assert result.step_up_token
    stored = db_session.query(AdminStepUpToken).one()
    assert result.step_up_token.encode() not in stored.token_hash
    consume_step_up(
        db_session,
        actor=actor,
        raw_token=result.step_up_token,
        purpose="account_reset_pin",
        now=identity_fixed_now,
    )
    with pytest.raises(StepUpRequired):
        consume_step_up(
            db_session,
            actor=actor,
            raw_token=result.step_up_token,
            purpose="account_reset_pin",
            now=identity_fixed_now,
        )
