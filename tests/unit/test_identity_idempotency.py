from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.identity.idempotency import (
    IdempotencyConflict,
    RequestInProgress,
    claim_idempotency,
    complete_idempotency,
    request_digest,
)


NOW = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
ACTOR = SimpleNamespace(account_id=uuid4())


class Session:
    def __init__(self, existing=None, inserted_id=None):
        self.existing = existing
        self.inserted_id = inserted_id
        self.execute_calls = 0

    def execute(self, _statement):
        self.execute_calls += 1
        return SimpleNamespace(scalar_one_or_none=lambda: self.inserted_id)

    def scalar(self, _statement):
        return self.existing

    def flush(self):
        return None


def test_idempotency_claim_complete_and_identical_replay():
    digest = request_digest({"session_id": "00000000-0000-4000-8000-000000000001"})
    record_id = uuid4()
    session = Session(inserted_id=record_id)
    claim = claim_idempotency(session, ACTOR, key="logout-all-test-0001", action="auth.logout_all",
                              request_sha256=digest, now=NOW)
    assert session.execute_calls == 1
    session.existing = SimpleNamespace(
        id=record_id,
        status="in_progress",
        response_status=None,
        response_reference={},
        request_sha256=digest,
        expires_at=NOW.replace(year=2027),
        completed_at=None,
    )
    complete_idempotency(session, claim, response_status=200,
                         response_reference={"signed_out": True}, now=NOW)
    replay = claim_idempotency(Session(session.existing), ACTOR, key="logout-all-test-0001",
                               action="auth.logout_all", request_sha256=digest, now=NOW)
    assert replay.replayed is True
    assert replay.response_reference == {"signed_out": True}


def test_same_key_changed_request_is_conflict_and_keys_are_closed():
    digest = request_digest({})
    record_id = uuid4()
    first = Session(inserted_id=record_id)
    claim_idempotency(first, ACTOR, key="logout-all-test-0002", action="auth.logout_all",
                      request_sha256=digest, now=NOW)
    first.existing = SimpleNamespace(
        id=record_id,
        status="in_progress",
        response_status=None,
        response_reference={},
        request_sha256=digest,
        expires_at=NOW.replace(year=2027),
        completed_at=None,
    )
    with pytest.raises(IdempotencyConflict):
        claim_idempotency(Session(first.existing), ACTOR, key="logout-all-test-0002",
                          action="auth.logout_all", request_sha256=b"x" * 32, now=NOW)
    with pytest.raises(ValueError, match="idempotency key"):
        claim_idempotency(Session(), ACTOR, key="bad key", action="auth.logout_all",
                          request_sha256=digest, now=NOW)


def test_identical_pending_request_has_distinct_retryable_outcome():
    digest = request_digest({"operation": "logout"})
    pending = SimpleNamespace(
        id=uuid4(), status="in_progress", response_status=None,
        response_reference={}, request_sha256=digest,
        expires_at=NOW.replace(year=2027), completed_at=None,
    )
    with pytest.raises(RequestInProgress):
        claim_idempotency(
            Session(pending), ACTOR, key="logout-pending-0001",
            action="auth.logout", request_sha256=digest, now=NOW,
        )
