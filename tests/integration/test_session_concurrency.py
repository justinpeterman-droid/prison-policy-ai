from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Lock
from uuid import uuid4

from sqlalchemy import select

from backend.identity.sessions import SessionReauthenticationRequired, renew_session
from backend.persistence.models import AccessSession
from tests.integration.identity_fixtures import (
    TEST_IDENTITY_SETTINGS,
    issue_fictional_tokens,
    seed_fictional_account,
)


class ThreadSafeAuditWriter:
    def __init__(self):
        self.events = []
        self.lock = Lock()

    def append(self, _session, event):
        with self.lock:
            self.events.append(event)
        return uuid4()


def test_two_renewals_have_one_winner_and_replay_revokes_family(db_session_factory):
    now = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
    with db_session_factory.begin() as session:
        account = seed_fictional_account(
            session, employee_number="TEST-7001", role="user", pin="Z9Y8X7", now=now
        )
        issued = issue_fictional_tokens(
            session, account=account, device_id="device-concurrent-0001", now=now
        )
        session_id = issued.session_id
        supplied = issued.renewal_token

    audit = ThreadSafeAuditWriter()

    def attempt():
        pending = None
        pair = None
        with db_session_factory.begin() as session:
            try:
                pair = renew_session(
                    session,
                    supplied_renewal_token=supplied,
                    device_id="device-concurrent-0001",
                    now=now + timedelta(minutes=1),
                    settings=TEST_IDENTITY_SETTINGS,
                    audit_writer=audit,
                    request_id="request-renew-race",
                )
            except SessionReauthenticationRequired as error:
                pending = error
        return (
            "reauthentication_required"
            if pending
            else ("rotated" if pair else "unknown")
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: attempt(), range(2)))
    assert sorted(results) == ["reauthentication_required", "rotated"]
    with db_session_factory() as session:
        stored = session.get(AccessSession, session_id)
        assert stored.revoked_at is not None
        assert stored.revoke_reason == "renewal_reuse"
        assert (
            session.scalar(
                select(AccessSession.id).where(
                    AccessSession.access_token_hash == stored.access_token_hash,
                    AccessSession.revoked_at.is_(None),
                )
            )
            is None
        )
