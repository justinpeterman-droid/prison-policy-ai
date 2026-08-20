from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from backend.identity.browser_admin import (
    BrowserAdminState,
    BrowserAdminStepUpRequired,
    enter_browser_admin_center,
    issue_browser_admin_step_up,
)


class FakeAudit:
    def __init__(self):
        self.events = []

    def append(self, _session, event):
        self.events.append(event)


class FakeSession:
    def __init__(self):
        self.confirmations = []


def test_browser_admin_state_is_safe_and_contains_no_credential_fields():
    deadline = datetime(2026, 8, 19, 20, 15, tzinfo=UTC)
    state = BrowserAdminState(elevated=True, elevation_expires_at=deadline)

    assert state.elevated is True
    assert state.elevation_expires_at == deadline
    assert "token" not in repr(state).lower()
    assert "pin" not in repr(state).lower()


def test_browser_admin_step_up_rejects_unknown_purpose_before_issuing(monkeypatch):
    session = FakeSession()
    actor = SimpleNamespace(role="admin")

    with pytest.raises(ValueError, match="purpose"):
        issue_browser_admin_step_up(
            session,
            actor=actor,
            pin="Q7W9E2",
            purpose="invented_admin_action",
            now=datetime(2026, 8, 19, 20, 0, tzinfo=UTC),
            audit_writer=FakeAudit(),
            request_id="request-admin-invalid-purpose",
        )


def test_non_admin_cannot_enter_browser_admin_center():
    actor = SimpleNamespace(role="user")

    with pytest.raises(PermissionError):
        enter_browser_admin_center(
            FakeSession(),
            actor=actor,
            pin="Q7W9E2",
            now=datetime(2026, 8, 19, 20, 0, tzinfo=UTC),
            audit_writer=FakeAudit(),
            request_id="request-admin-user-denied",
        )


def test_step_up_wrapper_requires_a_real_token(monkeypatch):
    from backend.identity import browser_admin as module

    now = datetime(2026, 8, 19, 20, 0, tzinfo=UTC)
    actor = SimpleNamespace(role="admin")
    monkeypatch.setattr(
        module,
        "confirm_admin_pin",
        lambda *args, **kwargs: SimpleNamespace(
            elevation_expires_at=now + timedelta(minutes=15),
            step_up_token=None,
            step_up_expires_at=None,
            purpose="account_reset_pin",
        ),
    )

    with pytest.raises(BrowserAdminStepUpRequired):
        issue_browser_admin_step_up(
            FakeSession(),
            actor=actor,
            pin="Q7W9E2",
            purpose="account_reset_pin",
            now=now,
            audit_writer=FakeAudit(),
            request_id="request-admin-missing-token",
        )
