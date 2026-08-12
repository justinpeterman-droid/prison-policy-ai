import pytest

from backend.identity.audit import AuditEventInput, AuditWriter, validate_details
from backend.persistence.base import Base
from backend.persistence.models import AuditEvent


def test_all_identity_tables_are_registered():
    assert {
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
    } <= set(Base.metadata.tables)
    assert AuditEvent.__tablename__ == "audit_events"


def test_audit_details_are_closed_and_size_bounded():
    assert validate_details("auth.login_failed", {"reason": "invalid_pin"}) == {
        "reason": "invalid_pin"
    }
    with pytest.raises(ValueError, match="audit details are invalid"):
        validate_details("auth.login_failed", {"pin": "fictional"})
    with pytest.raises(ValueError, match="audit details are invalid"):
        validate_details("unknown.action", {})
    with pytest.raises(ValueError, match="audit details are too large"):
        validate_details("auth.login_failed", {"reason": "x" * 5000})


def test_audit_contract_is_importable():
    assert AuditEventInput.__dataclass_fields__["request_id"]
    assert hasattr(AuditWriter, "append")
