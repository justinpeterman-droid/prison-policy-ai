from abc import abstractmethod
from dataclasses import dataclass
import json
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session


AUDIT_ACTION_FIELDS = {
    "auth.login_succeeded": {"persistent"},
    "auth.login_failed": {"reason"},
    "auth.locked": {"lock_minutes"},
    "auth.session_renewed": {"persistent"},
    "auth.session_revoked": {"reason"},
    "auth.logout_all": {"session_count"},
    "auth.pin_changed": set(),
    "auth.pin_reset": {"target_account_id"},
    "auth.step_up_succeeded": {"purpose"},
    "auth.step_up_failed": {"purpose", "reason"},
    "admin.staff_created": {"target_staff_id"},
    "admin.staff_updated": {"target_staff_id", "changed_fields"},
    "admin.account_created": {"target_account_id", "role"},
    "admin.account_role_changed": {"target_account_id", "old_role", "new_role"},
    "admin.account_deactivated": {"target_account_id"},
    "admin.account_reactivated": {"target_account_id"},
    "admin.account_unlocked": {"target_account_id"},
    "admin.review_lab_handoff_issued": {"handoff_id"},
    "admin.review_lab_handoff_redeemed": {"handoff_id", "browser_session_id"},
}


@dataclass(frozen=True)
class AuditEventInput:
    actor_account_id: UUID | None
    actor_staff_member_id: UUID | None
    action: str
    result: str
    request_id: str
    target_type: str
    target_id: UUID | None
    details: dict


class AuditWriter(Protocol):
    @abstractmethod
    def append(self, session: Session, event: AuditEventInput) -> UUID:
        """Append one validated audit event in the caller's transaction."""


def validate_details(action: str, details: dict) -> dict:
    allowed = AUDIT_ACTION_FIELDS.get(action)
    if allowed is None or not isinstance(details, dict) or not set(details) <= allowed:
        raise ValueError("audit details are invalid")
    encoded = json.dumps(details, sort_keys=True, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > 4096:
        raise ValueError("audit details are too large")
    return dict(details)
