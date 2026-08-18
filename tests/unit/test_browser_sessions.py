from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.identity import browser_sessions
from backend.identity.browser_sessions import (
    BrowserActor,
    BrowserCsrfInvalid,
    create_browser_session,
    renew_browser_session,
    resolve_browser_actor,
    validate_browser_csrf,
)
from backend.persistence.models import Account
from backend.persistence.models.browser import BrowserSessionBinding
from backend.persistence.models.sessions import AccessSession


class FakeSession:
    def __init__(self, values=None):
        self.values = values or {}
        self.added = []

    def get(self, model, key):
        return self.values.get((model, key))

    def add(self, value):
        self.added.append(value)


def _identity_state():
    session_id = uuid4()
    account_id = uuid4()
    staff_id = uuid4()
    stored = SimpleNamespace(id=session_id, account_id=account_id)
    account = SimpleNamespace(
        id=account_id,
        staff_member_id=staff_id,
        role="user",
        auth_version=3,
        must_change_pin=False,
    )
    return session_id, account_id, staff_id, stored, account


def _pair(session_id, now):
    return SimpleNamespace(
        session_id=session_id,
        access_token="access-value",
        renewal_token="renewal-value",
        access_expires_at=now + timedelta(minutes=15),
        renewal_expires_at=now + timedelta(hours=12),
        persistent=False,
    )


def test_create_browser_session_returns_safe_actor_and_cookie_material(monkeypatch):
    now = datetime(2026, 8, 18, 18, 0, tzinfo=UTC)
    session_id, account_id, staff_id, stored, account = _identity_state()
    db = FakeSession({
        (AccessSession, session_id): stored,
        (Account, account_id): account,
    })
    monkeypatch.setattr(browser_sessions, "login", lambda *args, **kwargs: _pair(session_id, now))
    monkeypatch.setattr(
        browser_sessions,
        "issue_credential",
        lambda: SimpleNamespace(raw="csrf-value", digest=b"c" * 32),
    )

    actor, cookies = create_browser_session(
        db,
        employee_number="12345",
        pin="1234",
        device_id="device-value",
        device_label="Test browser",
        persistent=False,
        now=now,
        settings=SimpleNamespace(),
        audit_writer=object(),
        request_id="req-browser-login",
    )

    assert actor == BrowserActor(
        account_id=account_id,
        staff_member_id=staff_id,
        session_id=session_id,
        role="user",
        auth_version=3,
        must_change_pin=False,
    )
    assert cookies.access_token == "access-value"
    assert cookies.renewal_token == "renewal-value"
    assert cookies.csrf_token == "csrf-value"
    assert len(db.added) == 1
    assert isinstance(db.added[0], BrowserSessionBinding)
    assert db.added[0].csrf_token_hash == b"c" * 32


def test_resolve_browser_actor_uses_existing_opaque_session_service(monkeypatch):
    now = datetime(2026, 8, 18, 18, 0, tzinfo=UTC)
    session_id, account_id, staff_id, stored, account = _identity_state()
    monkeypatch.setattr(
        browser_sessions,
        "resolve_access_session",
        lambda db, *, access_token, now: (stored, account),
    )

    actor = resolve_browser_actor(FakeSession(), access_token="opaque", now=now)

    assert actor.session_id == session_id
    assert actor.account_id == account_id
    assert actor.staff_member_id == staff_id


def test_validate_browser_csrf_rejects_missing_or_wrong_value(monkeypatch):
    session_id, account_id, staff_id, _, _ = _identity_state()
    actor = BrowserActor(account_id, staff_id, session_id, "user", 1, False)
    binding = SimpleNamespace(csrf_token_hash=b"a" * 32)
    db = FakeSession({(BrowserSessionBinding, session_id): binding})
    monkeypatch.setattr(browser_sessions, "hash_token", lambda value: b"b" * 32)

    with pytest.raises(BrowserCsrfInvalid):
        validate_browser_csrf(db, actor=actor, supplied_token="")
    with pytest.raises(BrowserCsrfInvalid):
        validate_browser_csrf(db, actor=actor, supplied_token="wrong")


def test_validate_browser_csrf_accepts_matching_digest(monkeypatch):
    session_id, account_id, staff_id, _, _ = _identity_state()
    actor = BrowserActor(account_id, staff_id, session_id, "user", 1, False)
    binding = SimpleNamespace(csrf_token_hash=b"a" * 32)
    db = FakeSession({(BrowserSessionBinding, session_id): binding})
    monkeypatch.setattr(browser_sessions, "hash_token", lambda value: b"a" * 32)

    validate_browser_csrf(db, actor=actor, supplied_token="matching")


def test_renew_browser_session_rotates_csrf_with_identity_credentials(monkeypatch):
    now = datetime(2026, 8, 18, 18, 0, tzinfo=UTC)
    session_id, account_id, _, stored, account = _identity_state()
    binding = SimpleNamespace(csrf_token_hash=b"a" * 32, rotated_at=now - timedelta(minutes=5))
    db = FakeSession({
        (AccessSession, session_id): stored,
        (Account, account_id): account,
        (BrowserSessionBinding, session_id): binding,
    })
    monkeypatch.setattr(browser_sessions, "renew_session", lambda *args, **kwargs: _pair(session_id, now))
    monkeypatch.setattr(browser_sessions, "hash_token", lambda value: b"a" * 32)
    monkeypatch.setattr(
        browser_sessions,
        "issue_credential",
        lambda: SimpleNamespace(raw="next-csrf", digest=b"z" * 32),
    )

    _, cookies = renew_browser_session(
        db,
        renewal_token="renewal-value",
        device_id="device-value",
        csrf_token="old-csrf",
        now=now,
        settings=SimpleNamespace(),
        audit_writer=object(),
        request_id="req-browser-renew",
    )

    assert cookies.csrf_token == "next-csrf"
    assert binding.csrf_token_hash == b"z" * 32
    assert binding.rotated_at == now
