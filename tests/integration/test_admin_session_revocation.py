from types import SimpleNamespace

from backend.identity.accounts import revoke_account_sessions
from backend.persistence.models.sessions import AccessSession


class Audit:
    def __init__(self): self.events = []
    def append(self, _session, event): self.events.append(event)


def test_revoke_all_invalidates_version_and_every_live_session(
    db_session, fictional_user_account, fictional_user_tokens,
    fictional_admin_account, fictional_admin_tokens, identity_fixed_now,
):
    actor = SimpleNamespace(
        account_id=fictional_admin_account.id,
        staff_member_id=fictional_admin_account.staff_member_id,
        session_id=fictional_admin_tokens.session_id,
        role="admin", auth_version=fictional_admin_account.auth_version,
    )
    before = fictional_user_account.auth_version
    audit = Audit()
    revoked = revoke_account_sessions(
        db_session, actor=actor, target_account_id=fictional_user_account.id,
        scope="all", target_session_id=None, now=identity_fixed_now,
        audit_writer=audit, request_id="request-revoke-all-1",
    )
    assert revoked == [fictional_user_tokens.session_id]
    assert fictional_user_account.auth_version == before + 1
    stored = db_session.get(AccessSession, fictional_user_tokens.session_id)
    assert stored.revoked_at == identity_fixed_now
    assert any(event.action == "auth.logout_all" for event in audit.events)
