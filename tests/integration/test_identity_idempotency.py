from datetime import timedelta

from backend.identity.idempotency import claim_idempotency, complete_idempotency, request_digest
from backend.webapp.api_v1.middleware import Actor


def test_completed_idempotency_reference_is_durable(
    db_session, fictional_user_account, fictional_user_tokens, identity_fixed_now
):
    actor = Actor(
        fictional_user_account.id, fictional_user_account.staff_member_id,
        fictional_user_tokens.session_id, "user", fictional_user_account.auth_version, False,
    )
    digest = request_digest({"operation": "logout-all"})
    claim = claim_idempotency(
        db_session, actor, key="logout-all-integration-0001", action="auth.logout_all",
        request_sha256=digest, now=identity_fixed_now,
    )
    complete_idempotency(
        db_session, claim, response_status=200,
        response_reference={"signed_out": True}, now=identity_fixed_now,
    )
    db_session.commit()
    replay = claim_idempotency(
        db_session, actor, key="logout-all-integration-0001", action="auth.logout_all",
        request_sha256=digest, now=identity_fixed_now + timedelta(seconds=1),
    )
    assert replay.replayed is True
    assert replay.response_reference == {"signed_out": True}
