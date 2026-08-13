import pytest

from backend.identity.audit import AuditEventInput, PostgresAuditWriter
from backend.persistence.models import AuditEvent


def test_postgres_audit_writer_inserts_through_append_function(
    db_session, fictional_user_account
):
    event_id = PostgresAuditWriter().append(
        db_session,
        AuditEventInput(
            fictional_user_account.id,
            fictional_user_account.staff_member_id,
            "auth.logout_all",
            "success",
            "request-audit-integration-1",
            "account",
            fictional_user_account.id,
            {"session_count": 0},
            client_version="1.0.0",
        ),
    )
    db_session.flush()
    assert db_session.get(AuditEvent, event_id).action == "auth.logout_all"


def test_audit_failure_rolls_back_caller_owned_state(
    db_session_factory,
    db_session,
    fictional_user_account,
):
    account_id = fictional_user_account.id
    account_type = type(fictional_user_account)
    original = fictional_user_account.auth_version
    db_session.commit()

    with pytest.raises(ValueError, match="actor attribution"):
        with db_session_factory.begin() as session:
            account = session.get(account_type, account_id)
            assert account is not None
            account.auth_version += 1
            PostgresAuditWriter().append(
                session,
                AuditEventInput(
                    None,
                    None,
                    "auth.logout_all",
                    "success",
                    "request-audit-invalid",
                    "account",
                    account_id,
                    {"session_count": 0},
                ),
            )

    with db_session_factory() as session:
        account = session.get(account_type, account_id)
        assert account is not None
        assert account.auth_version == original
