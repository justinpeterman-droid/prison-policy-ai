from uuid import uuid4

import pytest

from backend.identity.audit import AuditEventInput, PostgresAuditWriter


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class Session:
    def __init__(self):
        self.parameters = None

    def execute(self, _statement, parameters):
        self.parameters = parameters
        return Result(uuid4())


def test_postgres_audit_writer_validates_and_passes_only_safe_fields():
    session = Session()
    event = AuditEventInput(
        uuid4(), uuid4(), "auth.logout_all", "success", "request-audit-1",
        "account", uuid4(), {"session_count": 2}, client_version="1.0.0",
        device_id_hash=b"d" * 32, network_hash=b"n" * 32,
    )
    event_id = PostgresAuditWriter().append(session, event)
    assert event_id
    assert session.parameters["details"] == '{"session_count":2}'
    assert set(session.parameters) == {
        "actor_account_id", "actor_staff_member_id", "action", "target_type", "target_id",
        "result", "request_id", "client_version", "device_id_hash", "network_hash", "details",
    }


def test_audit_writer_rejects_null_actor_for_protected_action_before_sql():
    session = Session()
    with pytest.raises(ValueError, match="actor attribution"):
        PostgresAuditWriter().append(session, AuditEventInput(
            None, None, "auth.logout_all", "success", "request-audit-2",
            "account", None, {"session_count": 0},
        ))
    assert session.parameters is None


def test_audit_writer_rejects_unhashed_or_malformed_identity_dimensions():
    session = Session()
    with pytest.raises(ValueError, match="audit hash"):
        PostgresAuditWriter().append(session, AuditEventInput(
            uuid4(), uuid4(), "auth.logout_all", "success", "request-audit-3",
            "account", uuid4(), {"session_count": 1}, device_id_hash=b"raw-device",
        ))
    assert session.parameters is None
