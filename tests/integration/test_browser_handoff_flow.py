from datetime import timedelta
from types import SimpleNamespace

import pytest

from backend.identity.browser_handoffs import (
    HandoffInvalid,
    issue_browser_handoff,
    redeem_browser_handoff,
)
from backend.persistence.models.security import BrowserSession
from backend.persistence.models.sessions import AdminElevation
from backend.persistence.models.sessions import AdminStepUpToken
from backend.identity.tokens import hash_token


class Audit:
    def append(self, _session, event):
        return event.target_id


def test_handoff_replay_is_rejected_and_browser_session_is_attributable(
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
    db_session.add(
        AdminElevation(
            session_id=actor.session_id,
            issued_at=identity_fixed_now,
            last_used_at=identity_fixed_now,
            idle_expires_at=identity_fixed_now + timedelta(minutes=15),
        )
    )
    step_up_token = "fictional-review-lab-step-up-token-0000000001"
    db_session.add(
        AdminStepUpToken(
            session_id=actor.session_id,
            token_hash=hash_token(step_up_token),
            purpose="review_lab_handoff",
            issued_at=identity_fixed_now,
            expires_at=identity_fixed_now + timedelta(minutes=5),
        )
    )
    db_session.flush()
    issued = issue_browser_handoff(
        db_session,
        actor=actor,
        now=identity_fixed_now,
        audit_writer=Audit(),
        request_id="request-integration-handoff-1",
        step_up_token=step_up_token,
    )
    redeemed = redeem_browser_handoff(
        db_session,
        raw_token=issued.token,
        now=identity_fixed_now + timedelta(seconds=1),
        audit_writer=Audit(),
        request_id="request-integration-handoff-2",
    )
    db_session.flush()
    stored = db_session.get(BrowserSession, redeemed.browser_session_id)
    assert stored.account_id == fictional_admin_account.id
    assert stored.issuing_session_id == fictional_admin_tokens.session_id
    with pytest.raises(HandoffInvalid):
        redeem_browser_handoff(
            db_session,
            raw_token=issued.token,
            now=identity_fixed_now + timedelta(seconds=2),
            audit_writer=Audit(),
            request_id="request-integration-handoff-3",
        )
