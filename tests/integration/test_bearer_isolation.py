from datetime import timedelta

from backend.identity.sessions import resolve_access_session


def test_fictional_bearer_resolves_server_owned_actor(
    db_session, fictional_user_account, fictional_user_tokens, identity_fixed_now
):
    stored, account = resolve_access_session(
        db_session,
        access_token=fictional_user_tokens.access_token,
        now=identity_fixed_now + timedelta(minutes=1),
    )
    assert account.id == fictional_user_account.id
    assert stored.account_id == fictional_user_account.id
    assert account.role == "user"


def test_legacy_cookie_value_cannot_resolve_as_access_token(
    db_session, identity_fixed_now
):
    from backend.identity.sessions import SessionReauthenticationRequired
    import pytest

    with pytest.raises(SessionReauthenticationRequired):
        resolve_access_session(
            db_session, access_token="fictional-legacy-cookie-value",
            now=identity_fixed_now,
        )
