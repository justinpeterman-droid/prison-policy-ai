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
    "incident.saved": {
        "incident_id", "revision_number", "changed_fields", "reason"},
    "incident.restored": {
        "incident_id", "revision_number", "source_revision_number"},
    "incident.status_changed": {"incident_id", "old_status", "new_status"},
    "report.created": {"report_id", "incident_id", "report_type"},
    "report.viewed_by_admin": {"report_id"},
    "report.saved": {"report_id", "revision_number", "changed_fields", "reason"},
    "report.restored": {
        "report_id", "revision_number", "source_revision_number"},
    "report.recovery_created": {
        "report_id", "revision_number", "source_revision_number"},
    "report.status_changed": {"report_id", "old_status", "new_status"},
    "report.ownership_transferred": {
        "report_id", "old_owner_staff_id", "new_owner_staff_id"},
    "report.exported": {"report_id", "export_id", "export_format"},
    "report.exported_by_admin": {"report_id", "export_id", "export_format"},
    "ai.job_submitted": {"job_id", "job_type", "incident_id"},
    "ai.job_succeeded": {"job_id", "job_type", "latency_ms"},
    "ai.job_failed": {"job_id", "job_type", "result_code"},
    # The question itself is a digest: policy questions quote incidents.
    "policy.question_answered": {
        "question_sha256", "document_count", "latency_ms"},
    "admin.report_search": {"filters", "result_count"},
    "admin.bulk_exported": {"export_id", "report_count"},
    "admin.audit_exported": {"export_id", "event_count"},
    "admin.health_viewed": set(),
}

#: Detail fields that carry *names* of fields or filters. Bounded by pattern so
#: a caller cannot smuggle report text through a list that reads as metadata.
AUDIT_NAME_LIST_FIELDS = frozenset({"changed_fields", "filters"})
AUDIT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
MAX_AUDIT_NAME_LIST = 100


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


def _validate_name_list(value: object) -> None:
    if not isinstance(value, list) or len(value) > MAX_AUDIT_NAME_LIST:
        raise ValueError("audit details are invalid")
    for name in value:
        if not isinstance(name, str) or not AUDIT_NAME_PATTERN.fullmatch(name):
            raise ValueError("audit details are invalid")


def validate_details(action: str, details: dict) -> dict:
    allowed = AUDIT_ACTION_FIELDS.get(action)
    if allowed is None or not isinstance(details, dict) or not set(details) <= allowed:
        raise ValueError("audit details are invalid")
    if action == "system.initial_admin_bootstrapped" and set(details) != allowed:
        raise ValueError("audit details are invalid")
    for key in AUDIT_NAME_LIST_FIELDS & set(details):
        _validate_name_list(details[key])
    encoded = json.dumps(details, sort_keys=True, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > 4096:
        raise ValueError("audit details are too large")
    return dict(details)


class PostgresAuditWriter:
    def append(self, session: Session, event: AuditEventInput) -> UUID:
        validate_actor_attribution(event)
        details = validate_details(event.action, event.details)
        for digest in (event.device_id_hash, event.network_hash):
            if digest is not None and (not isinstance(digest, bytes) or len(digest) != 32):
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
        return session.execute(statement, {
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
        }).scalar_one()
