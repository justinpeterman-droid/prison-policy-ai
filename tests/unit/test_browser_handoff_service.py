from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.identity.browser_handoffs import (
    HandoffInvalid,
    issue_browser_handoff,
    redeem_browser_handoff,
)
from backend.identity.elevation import AdminElevationRequired
from backend.identity.tokens import hash_token


NOW = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
STEP_UP = "fictional-review-lab-step-up-token-0000000001"


class RecordingAudit:
    def __init__(self):
        self.events = []

    def append(self, _session, event):
        self.events.append(event)
        return uuid4()


class FakeSession:
    def __init__(self, *scalars):
        self.scalars = list(scalars)
        self.added = []

    def scalar(self, _statement):
        return self.scalars.pop(0)

    def add(self, row):
        self.added.append(row)

    def flush(self):
        return None


def _actor():
    return SimpleNamespace(
        account_id=uuid4(),
        staff_member_id=uuid4(),
        session_id=uuid4(),
        role="admin",
        auth_version=3,
    )


def _issue_session(actor):
    access = SimpleNamespace(
        id=actor.session_id,
        account_id=actor.account_id,
        auth_version=actor.auth_version,
        revoked_at=None,
        access_expires_at=NOW + timedelta(minutes=10),
    )
    account = SimpleNamespace(
        id=actor.account_id,
        staff_member_id=actor.staff_member_id,
        auth_version=actor.auth_version,
        role="admin",
        status="active",
    )
    staff = SimpleNamespace(id=actor.staff_member_id, is_active=True)
    elevation = SimpleNamespace(
        session_id=actor.session_id,
        revoked_at=None,
        last_used_at=NOW,
        idle_expires_at=NOW + timedelta(minutes=5),
    )
    step_up = SimpleNamespace(
        session_id=actor.session_id,
        purpose="review_lab_handoff",
        token_hash=hash_token(STEP_UP),
        used_at=None,
        revoked_at=None,
        expires_at=NOW + timedelta(minutes=5),
    )
    return FakeSession(access, account, staff, elevation, step_up)


def test_handoff_is_digest_only_and_expires_in_sixty_seconds():
    actor = _actor()
    audit = RecordingAudit()
    session = _issue_session(actor)

    result = issue_browser_handoff(
        session,
        actor=actor,
        now=NOW,
        audit_writer=audit,
        request_id="request-handoff-issue-1",
        step_up_token=STEP_UP,
    )

    assert result.expires_at == NOW + timedelta(seconds=60)
    assert result.token
    stored = session.added[0]
    assert stored.token_hash != result.token.encode("utf-8")
    assert result.token not in repr(stored.token_hash)
    assert audit.events[0].action == "admin.review_lab_handoff_issued"
    assert audit.events[0].details == {"handoff_id": str(result.handoff_id)}
    assert session.scalars == []


def test_handoff_redeem_is_single_use_and_creates_thirty_minute_session():
    actor = _actor()
    issue_session = _issue_session(actor)
    issued = issue_browser_handoff(
        issue_session,
        actor=actor,
        now=NOW,
        audit_writer=RecordingAudit(),
        request_id="request-handoff-issue-2",
        step_up_token=STEP_UP,
    )
    handoff = issue_session.added[0]
    access_session = SimpleNamespace(
        id=actor.session_id,
        account_id=actor.account_id,
        auth_version=3,
        revoked_at=None,
        renewal_expires_at=NOW + timedelta(hours=12),
    )
    account = SimpleNamespace(
        id=actor.account_id,
        staff_member_id=actor.staff_member_id,
        auth_version=3,
        role="admin",
        status="active",
    )
    staff = SimpleNamespace(id=actor.staff_member_id, is_active=True)
    audit = RecordingAudit()
    redeem_session = FakeSession(handoff, access_session, account, staff)

    redeemed = redeem_browser_handoff(
        redeem_session,
        raw_token=issued.token,
        now=NOW + timedelta(seconds=30),
        audit_writer=audit,
        request_id="request-handoff-redeem-1",
    )

    assert handoff.redeemed_at == NOW + timedelta(seconds=30)
    assert redeemed.expires_at == NOW + timedelta(minutes=30, seconds=30)
    stored_browser_session = redeem_session.added[0]
    assert stored_browser_session.token_hash != redeemed.cookie_value.encode("utf-8")
    assert audit.events[0].action == "admin.review_lab_handoff_redeemed"

    replay_session = FakeSession(handoff)
    with pytest.raises(HandoffInvalid):
        redeem_browser_handoff(
            replay_session,
            raw_token=issued.token,
            now=NOW + timedelta(seconds=31),
            audit_writer=RecordingAudit(),
            request_id="request-handoff-replay-1",
        )


def test_expired_handoff_is_rejected_without_creating_browser_session():
    actor = _actor()
    issue_session = _issue_session(actor)
    issued = issue_browser_handoff(
        issue_session,
        actor=actor,
        now=NOW,
        audit_writer=RecordingAudit(),
        request_id="request-handoff-issue-3",
        step_up_token=STEP_UP,
    )
    redeem_session = FakeSession(issue_session.added[0])

    with pytest.raises(HandoffInvalid):
        redeem_browser_handoff(
            redeem_session,
            raw_token=issued.token,
            now=NOW + timedelta(seconds=60),
            audit_writer=RecordingAudit(),
            request_id="request-handoff-expired-1",
        )
    assert redeem_session.added == []


def test_issue_requires_a_live_access_actor_and_active_elevation():
    actor = _actor()
    revoked = _issue_session(actor)
    revoked.scalars[0].revoked_at = NOW
    with pytest.raises(HandoffInvalid):
        issue_browser_handoff(
            revoked,
            actor=actor,
            now=NOW,
            audit_writer=RecordingAudit(),
            request_id="request-handoff-revoked-1",
            step_up_token=STEP_UP,
        )
    assert revoked.added == []

    expired = _issue_session(actor)
    expired.scalars[3].idle_expires_at = NOW
    with pytest.raises(AdminElevationRequired):
        issue_browser_handoff(
            expired,
            actor=actor,
            now=NOW,
            audit_writer=RecordingAudit(),
            request_id="request-handoff-elevation-1",
            step_up_token=STEP_UP,
        )
    assert expired.added == []


def test_issue_service_rejects_missing_or_wrong_purpose_step_up():
    actor = _actor()
    session = _issue_session(actor)
    session.scalars[4] = None
    with pytest.raises(Exception) as caught:
        issue_browser_handoff(
            session,
            actor=actor,
            now=NOW,
            audit_writer=RecordingAudit(),
            request_id="request-handoff-step-up-1",
            step_up_token="fictional-wrong-step-up-token-0000000000001",
        )
    assert getattr(caught.value, "code", None) == "step_up_required"
    assert session.added == []
