from abc import abstractmethod
from dataclasses import dataclass
import json
import re
from typing import Protocol
from uuid import UUID

from sqlalchemy import text
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
    "system.initial_admin_bootstrapped": {
        "operation_id",
        "approval_reference_sha256",
    },
    # Reporting. Audit rows outlive the report they describe and are exported
    # to oversight, so an action may record identifiers, revision numbers,
    # counts, digests and latency — never field notes, report or policy text,
    # staff names, employee numbers, or inmate identifiers.
    "incident.created": {"incident_id"},
    "incident.saved": {"incident_id", "revision_number", "changed_fields", "reason"},
    "incident.restored": {"incident_id", "revision_number", "source_revision_number"},
    "incident.status_changed": {"incident_id", "old_status", "new_status"},
    "report.created": {"report_id", "incident_id", "report_type"},
    "report.viewed_by_admin": {"report_id"},
    "report.saved": {"report_id", "revision_number", "changed_fields", "reason"},
    "report.restored": {"report_id", "revision_number", "source_revision_number"},
    "report.recovery_created": {
        "report_id",
        "revision_number",
        "source_revision_number",
    },
    "report.status_changed": {"report_id", "old_status", "new_status"},
    "report.ownership_transferred": {
        "report_id",
        "old_owner_staff_id",
        "new_owner_staff_id",
    },
    "report.exported": {"report_id", "export_id", "export_format"},
    "report.exported_by_admin": {"report_id", "export_id", "export_format"},
    "ai.job_submitted": {"job_id", "job_type", "incident_id"},
    "ai.job_succeeded": {"job_id", "job_type", "latency_ms"},
    "ai.job_failed": {"job_id", "job_type", "result_code"},
    # The question itself is a digest: policy questions quote incidents.
    "policy.question_answered": {"question_sha256", "document_count", "latency_ms"},
    "admin.report_search": {"filters", "result_count"},
    "admin.bulk_exported": {"export_id", "report_count"},
    "admin.audit_exported": {"export_id", "event_count"},
    "admin.health_viewed": set(),
}

#: Detail fields that carry *names* of fields or filters. Bounded by pattern so
#: a caller cannot smuggle report text through a list that reads as metadata.
AUDIT_NAME_LIST_FIELDS = frozenset({"changed_fields", "filters"})
AUDIT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
AUDIT_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MAX_AUDIT_NAME_LIST = 100
MAX_AUDIT_NUMBER = 1_000_000_000

AUDIT_UUID_FIELDS = frozenset(
    field
    for fields in AUDIT_ACTION_FIELDS.values()
    for field in fields
    if field.endswith("_id")
)
AUDIT_SHA256_FIELDS = frozenset(
    field
    for fields in AUDIT_ACTION_FIELDS.values()
    for field in fields
    if field.endswith("_sha256")
)
AUDIT_INTEGER_FIELDS = frozenset(
    {
        "lock_minutes",
        "session_count",
        "revision_number",
        "source_revision_number",
        "latency_ms",
        "document_count",
        "result_count",
        "report_count",
        "event_count",
    }
)
AUDIT_ENUM_FIELDS = {
    "role": frozenset({"user", "admin"}),
    "old_role": frozenset({"user", "admin"}),
    "new_role": frozenset({"user", "admin"}),
    "old_status": frozenset({"in_progress", "completed", "archived"}),
    "new_status": frozenset({"in_progress", "completed", "archived"}),
    "report_type": frozenset(
        {
            "first_person",
            "supervisor_summary",
            "cover_letter",
            "disciplinary",
            "investigation",
            "form_005",
        }
    ),
    "export_format": frozenset({"docx"}),
    "job_type": frozenset({"classify", "extract", "generate", "disciplinary"}),
}
AUDIT_CHANGED_FIELDS = {
    "incident.saved": frozenset(
        {
            "field_notes",
            "incident_date",
            "incident_time",
            "facility",
            "shift",
            "location",
            "category",
            "classification",
            "extracted_facts",
            "gap_answers",
            "charges",
            "validation",
        }
    ),
    "report.saved": frozenset(
        {
            "narrative",
            "editable_fields",
            "validation",
            "warnings",
        }
    ),
    "admin.staff_updated": frozenset(
        {
            "employee_number",
            "rank",
            "first_name",
            "last_name",
            "shift",
            "is_active",
        }
    ),
}
AUDIT_FILTER_FIELDS = frozenset(
    {
        "report_id",
        "incident_id",
        "reporting_staff_id",
        "preparer_staff_id",
        "incident_date_from",
        "incident_date_to",
        "created_at_from",
        "created_at_to",
        "inmate_first_name",
        "inmate_middle_name",
        "inmate_last_name",
        "inmate_adc_number",
        "category",
        "facility",
        "location",
        "shift",
        "status",
        "last_editor_staff_id",
        "modified_at_from",
        "modified_at_to",
    }
)
AUDIT_CODE_VALUES = {
    ("auth.login_failed", "reason"): frozenset(
        {
            "invalid_credentials",
            "account_locked_or_deactivated",
            "staff_inactive",
            "temporary_pin_expired",
            "invalid_pin",
        }
    ),
    ("auth.session_revoked", "reason"): frozenset(
        {
            "renewal_reuse",
            "user_revoked",
            "admin_action",
        }
    ),
    ("auth.step_up_failed", "reason"): frozenset({"invalid_confirmation"}),
    ("incident.saved", "reason"): frozenset(
        {
            "autosave",
            "manual_save",
            "ai_result",
        }
    ),
    ("report.saved", "reason"): frozenset(
        {
            "autosave",
            "manual_save",
            "ai_result",
            "admin_edit",
        }
    ),
}
AUDIT_PURPOSES = frozenset(
    {
        "admin_center",
        "staff_write",
        "account_create",
        "account_role_status",
        "account_reset_pin",
        "account_unlock",
        "account_revoke_sessions",
        "report_restore",
        "report_transfer",
        "bulk_export",
        "audit_export",
        "review_lab_handoff",
    }
)


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
    client_version: str | None = None
    device_id_hash: bytes | None = None
    network_hash: bytes | None = None


class AuditWriter(Protocol):
    @abstractmethod
    def append(self, session: Session, event: AuditEventInput) -> UUID:
        """Append one validated audit event in the caller's transaction."""


def validate_actor_attribution(event: AuditEventInput) -> None:
    has_account = event.actor_account_id is not None
    has_staff = event.actor_staff_member_id is not None
    if has_account != has_staff:
        raise ValueError("audit actor attribution is invalid")
    if event.action == "system.initial_admin_bootstrapped":
        if has_account:
            raise ValueError("audit actor attribution is invalid")
        return
    if not has_account and event.action != "auth.login_failed":
        raise ValueError("audit actor attribution is invalid")


def _validate_name_list(action: str, key: str, value: object) -> None:
    if not isinstance(value, list) or len(value) > MAX_AUDIT_NAME_LIST:
        raise ValueError("audit details are invalid")
    for name in value:
        if not isinstance(name, str) or not AUDIT_NAME_PATTERN.fullmatch(name):
            raise ValueError("audit details are invalid")
    if len(set(value)) != len(value):
        raise ValueError("audit details are invalid")
    if key == "changed_fields":
        allowed = AUDIT_CHANGED_FIELDS.get(action)
        if allowed is not None and not set(value) <= allowed:
            raise ValueError("audit details are invalid")
    elif key == "filters" and not set(value) <= AUDIT_FILTER_FIELDS:
        raise ValueError("audit details are invalid")


def _validate_detail_value(action: str, key: str, value: object) -> None:
    allowed_codes = AUDIT_CODE_VALUES.get((action, key))
    if allowed_codes is not None:
        if value not in allowed_codes:
            raise ValueError("audit details are invalid")
    elif key == "purpose":
        if value not in AUDIT_PURPOSES:
            raise ValueError("audit details are invalid")
    elif key in AUDIT_UUID_FIELDS:
        if not isinstance(value, str):
            raise ValueError("audit details are invalid")
        try:
            parsed = UUID(value)
        except (ValueError, AttributeError):
            raise ValueError("audit details are invalid") from None
        if str(parsed) != value.lower():
            raise ValueError("audit details are invalid")
    elif key in AUDIT_SHA256_FIELDS:
        if not isinstance(value, str) or not AUDIT_SHA256_PATTERN.fullmatch(value):
            raise ValueError("audit details are invalid")
    elif key in AUDIT_INTEGER_FIELDS:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or not 0 <= value <= MAX_AUDIT_NUMBER
        ):
            raise ValueError("audit details are invalid")
    elif key == "persistent":
        if not isinstance(value, bool):
            raise ValueError("audit details are invalid")
    elif key in AUDIT_ENUM_FIELDS:
        if value not in AUDIT_ENUM_FIELDS[key]:
            raise ValueError("audit details are invalid")
    elif key in {"reason", "purpose", "result_code"}:
        if not isinstance(value, str) or not AUDIT_NAME_PATTERN.fullmatch(value):
            raise ValueError("audit details are invalid")


def validate_details(action: str, details: dict) -> dict:
    allowed = AUDIT_ACTION_FIELDS.get(action)
    if allowed is None or not isinstance(details, dict) or not set(details) <= allowed:
        raise ValueError("audit details are invalid")
    if action == "system.initial_admin_bootstrapped" and set(details) != allowed:
        raise ValueError("audit details are invalid")
    try:
        encoded = json.dumps(details, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        raise ValueError("audit details are invalid") from None
    if len(encoded.encode("utf-8")) > 4096:
        raise ValueError("audit details are too large")
    for key in AUDIT_NAME_LIST_FIELDS & set(details):
        _validate_name_list(action, key, details[key])
    for key, value in details.items():
        if key not in AUDIT_NAME_LIST_FIELDS:
            _validate_detail_value(action, key, value)
    return dict(details)


class PostgresAuditWriter:
    def append(self, session: Session, event: AuditEventInput) -> UUID:
        validate_actor_attribution(event)
        details = validate_details(event.action, event.details)
        for digest in (event.device_id_hash, event.network_hash):
            if digest is not None and (
                not isinstance(digest, bytes) or len(digest) != 32
            ):
                raise ValueError("audit hash is invalid")
        if event.client_version is not None and (
            not isinstance(event.client_version, str) or len(event.client_version) > 64
        ):
            raise ValueError("audit client version is invalid")
        statement = text(
            "SELECT append_audit_event("
            ":actor_account_id, :actor_staff_member_id, :action, :target_type, "
            ":target_id, :result, :request_id, :client_version, :device_id_hash, "
            ":network_hash, CAST(:details AS jsonb))"
        )
        return session.execute(
            statement,
            {
                "actor_account_id": event.actor_account_id,
                "actor_staff_member_id": event.actor_staff_member_id,
                "action": event.action,
                "target_type": event.target_type,
                "target_id": event.target_id,
                "result": event.result,
                "request_id": event.request_id,
                "client_version": event.client_version,
                "device_id_hash": event.device_id_hash,
                "network_hash": event.network_hash,
                "details": json.dumps(details, separators=(",", ":"), sort_keys=True),
            },
        ).scalar_one()
