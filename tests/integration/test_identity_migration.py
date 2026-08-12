from sqlalchemy import inspect, text


EXPECTED_TABLES = {
    "staff_members",
    "accounts",
    "sessions",
    "renewal_token_history",
    "admin_elevations",
    "admin_step_up_tokens",
    "browser_handoffs",
    "browser_sessions",
    "auth_rate_limits",
    "audit_events",
}


def test_identity_upgrade_creates_complete_schema(db_engine):
    assert EXPECTED_TABLES <= set(inspect(db_engine).get_table_names())


def test_audit_rows_cannot_be_updated_or_deleted(db_engine):
    with db_engine.begin() as connection:
        event_id = connection.execute(text(
            "SELECT append_audit_event(NULL, NULL, 'auth.login_failed', "
            "'account', NULL, 'failed', 'request-test-1', '1.0.0', NULL, NULL, "
            "'{\"reason\":\"unknown\"}'::jsonb)"
        )).scalar_one()
    for statement in (
        text("UPDATE audit_events SET result='success' WHERE id=:id"),
        text("DELETE FROM audit_events WHERE id=:id"),
    ):
        try:
            with db_engine.begin() as connection:
                connection.execute(statement, {"id": event_id})
        except Exception as exc:
            assert "audit_events are append-only" in str(exc)
        else:
            raise AssertionError("audit mutation unexpectedly succeeded")
