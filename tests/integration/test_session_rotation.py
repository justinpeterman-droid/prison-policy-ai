from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.identity.sessions import SessionReauthenticationRequired, renew_session
from backend.identity.tokens import hash_token
from backend.persistence.models import AccessSession, RenewalTokenHistory
from tests.integration.identity_fixtures import TEST_IDENTITY_SETTINGS


class RecordingAuditWriter:
    def __init__(self):
        self.events = []

    def append(self, _session, event):
        self.events.append(event)
        return uuid4()


def test_rotation_persists_only_hashes_and_replay_revokes_family(db_session, fictional_user_tokens, identity_fixed_now):
    audit = RecordingAuditWriter()
    old_raw = fictional_user_tokens.renewal_token
    rotated = renew_session(
        db_session,
        supplied_renewal_token=old_raw,
        device_id="device-fictional-user-0001",
        now=identity_fixed_now + timedelta(minutes=1),
        settings=TEST_IDENTITY_SETTINGS,
        audit_writer=audit,
        request_id="request-rotation-1",
    )
    db_session.flush()
    stored = db_session.get(AccessSession, fictional_user_tokens.session_id)
    history = db_session.scalar(select(RenewalTokenHistory).where(RenewalTokenHistory.session_id == stored.id))
    assert stored.renewal_token_hash == hash_token(rotated.renewal_token)
    assert history.token_hash == hash_token(old_raw)
    assert old_raw.encode("utf-8") not in stored.renewal_token_hash

    with pytest.raises(SessionReauthenticationRequired):
        renew_session(
            db_session,
            supplied_renewal_token=old_raw,
            device_id="device-fictional-user-0001",
            now=identity_fixed_now + timedelta(minutes=2),
            settings=TEST_IDENTITY_SETTINGS,
            audit_writer=audit,
            request_id="request-replay-1",
        )
    assert stored.revoked_at == identity_fixed_now + timedelta(minutes=2)
    assert stored.revoke_reason == "renewal_reuse"


def test_device_mismatch_requires_reauthentication_without_rotation(
    db_session, fictional_user_tokens, identity_fixed_now
):
    before = db_session.get(AccessSession, fictional_user_tokens.session_id).renewal_token_hash
    with pytest.raises(SessionReauthenticationRequired):
        renew_session(
            db_session,
            supplied_renewal_token=fictional_user_tokens.renewal_token,
            device_id="device-fictional-wrong-0001",
            now=identity_fixed_now + timedelta(minutes=1),
            settings=TEST_IDENTITY_SETTINGS,
            audit_writer=RecordingAuditWriter(),
            request_id="request-device-1",
        )
    assert db_session.get(AccessSession, fictional_user_tokens.session_id).renewal_token_hash == before


def test_replay_revocation_commits_before_error_is_exposed(db_session_factory):
    from tests.integration.identity_fixtures import (
        issue_fictional_tokens,
        seed_fictional_account,
    )

    now = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
    with db_session_factory.begin() as session:
        account = seed_fictional_account(session, employee_number="TEST-7101", role="user", pin="Z9Y8X7", now=now)
        issued = issue_fictional_tokens(session, account=account, device_id="device-replay-commit-0001", now=now)
        session_id = issued.session_id
        old_renewal = issued.renewal_token

    with db_session_factory.begin() as session:
        renew_session(
            session,
            supplied_renewal_token=old_renewal,
            device_id="device-replay-commit-0001",
            now=now + timedelta(minutes=1),
            settings=TEST_IDENTITY_SETTINGS,
            audit_writer=RecordingAuditWriter(),
            request_id="request-replay-commit-rotate",
        )

    pending = None
    with db_session_factory.begin() as session:
        try:
            renew_session(
                session,
                supplied_renewal_token=old_renewal,
                device_id="device-replay-commit-0001",
                now=now + timedelta(minutes=2),
                settings=TEST_IDENTITY_SETTINGS,
                audit_writer=RecordingAuditWriter(),
                request_id="request-replay-commit-detect",
            )
        except SessionReauthenticationRequired as error:
            pending = error
    assert pending is not None
    with db_session_factory() as session:
        stored = session.get(AccessSession, session_id)
        assert stored.revoked_at == now + timedelta(minutes=2)
        assert stored.revoke_reason == "renewal_reuse"
