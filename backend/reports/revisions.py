"""Caller-owned, row-locked incident and report revision operations.

The request/session lifecycle owns the transaction.  Each operation locks the
current row, appends the immutable revision and audit event, updates current
state where appropriate, and flushes.  It never begins or commits, so an
idempotency record and all other caller work remain in the same atomic unit.
"""
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.identity.audit import AuditEventInput, AuditWriter, PostgresAuditWriter
from backend.persistence.models.reporting import (
    Incident,
    IncidentRevision,
    Report,
    ReportRevision,
)
from backend.reports.provenance import collect_provenance
from backend.webapp.api_v1.middleware import Actor
from backend.webapp.api_v1.schemas.reporting import (
    IncidentSnapshotV1,
    ReportContentV1,
    changed_field_names,
)


__all__ = [
    "Actor",
    "RevisionConflict",
    "RevisionTargetMissing",
    "create_recovery_revision",
    "restore_report",
    "save_incident",
    "save_report",
]

DEFAULT_CLIENT_VERSION = "0.0.0-development"
INCIDENT_SAVE_REASONS = frozenset({"autosave", "manual_save", "ai_result"})
REPORT_SAVE_REASONS = frozenset(
    {"autosave", "manual_save", "ai_result", "admin_edit"})
INCIDENT_CONTENT_FIELDS = (
    "incident_date",
    "incident_time",
    "facility",
    "shift",
    "location",
    "category",
    "field_notes",
    "classification",
    "extracted_facts",
    "gap_answers",
    "charges",
    "validation",
)
PROVENANCE_COLUMN_NAMES = (
    "fast_model",
    "pro_model",
    "model_location",
    "classification_prompt_sha256",
    "generation_prompt_sha256",
    "checklist_sha256",
    "template_sha256",
    "cloud_run_revision",
    "source_commit",
)


class RevisionTargetMissing(LookupError):
    """The incident/report or requested source revision does not exist."""


@dataclass(frozen=True)
class RevisionConflict(Exception):
    """Safe metadata describing a stale base revision."""

    current_revision_number: int
    status: str | None = None
    updated_at: datetime | None = None

    def __str__(self) -> str:
        return (
            "content was modified by another save; current revision is "
            f"{self.current_revision_number}"
        )


def _lock_row(session: Session, model, row_id: UUID):
    row = session.execute(
        select(model).where(model.id == row_id).with_for_update()
    ).scalar_one_or_none()
    if row is None:
        raise RevisionTargetMissing(f"{model.__name__} was not found")
    return row


def _next_revision_number(session: Session, model, column, parent_id: UUID) -> int:
    highest = session.execute(
        select(func.max(model.revision_number)).where(column == parent_id)
    ).scalar()
    return (highest or 0) + 1


def _metadata(
    request_id: str | None,
    client_version: str | None,
    audit_writer: AuditWriter | None,
) -> tuple[str, str, AuditWriter]:
    return (
        request_id or str(uuid4()),
        client_version or DEFAULT_CLIENT_VERSION,
        audit_writer or PostgresAuditWriter(),
    )


def _changed_fields(previous: dict | None, current: dict) -> dict[str, list[str]]:
    return {"fields": changed_field_names(previous, current)}


def _append_audit(
    session: Session,
    audit_writer: AuditWriter,
    actor: Actor,
    *,
    action: str,
    target_type: str,
    target_id: UUID,
    request_id: str,
    details: dict,
    client_version: str,
) -> None:
    audit_writer.append(session, AuditEventInput(
        actor_account_id=actor.account_id,
        actor_staff_member_id=actor.staff_member_id,
        action=action,
        result="success",
        request_id=request_id,
        target_type=target_type,
        target_id=target_id,
        details=details,
        client_version=client_version,
    ))


def _report_payload(content: ReportContentV1) -> dict:
    return ReportContentV1.model_validate(content).model_dump(mode="json")


def _ai_provenance(reason: str) -> dict[str, str | None]:
    return collect_provenance() if reason == "ai_result" else {}


def _source_revision_provenance(
    provenance: dict | None, source_revision_number: int,
) -> dict:
    source_revision_number = _validate_revision_number(
        source_revision_number, "source")
    return {
        **dict(provenance or {}),
        "source_revision_number": source_revision_number,
    }


def _incident_current_payload(incident: Incident) -> dict:
    values = {field: getattr(incident, field) for field in INCIDENT_CONTENT_FIELDS}
    return IncidentSnapshotV1.model_validate(values).model_dump(mode="json")


def _apply_incident_snapshot(
    incident: Incident, snapshot: IncidentSnapshotV1, payload: dict
) -> None:
    for field in INCIDENT_CONTENT_FIELDS:
        value = getattr(snapshot, field) if field in {"incident_date", "incident_time"} else payload[field]
        setattr(incident, field, value)


def _check_base(row, base_revision_number: int) -> None:
    if row.current_revision_number != base_revision_number:
        raise RevisionConflict(
            current_revision_number=row.current_revision_number,
            status=getattr(row.status, "value", row.status),
            updated_at=row.updated_at,
        )


def _validate_revision_number(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} revision number must be a nonnegative integer")
    return value


def save_report(
    session: Session,
    actor: Actor,
    report_id: UUID,
    content: ReportContentV1,
    base_revision_number: int,
    reason: str,
    *,
    request_id: str | None = None,
    client_version: str | None = None,
    audit_writer: AuditWriter | None = None,
) -> ReportRevision:
    """Append and promote one validated report revision in the caller transaction."""
    base_revision_number = _validate_revision_number(base_revision_number, "base")
    if reason not in REPORT_SAVE_REASONS:
        raise ValueError("report revision reason is invalid")
    request_id, client_version, audit_writer = _metadata(
        request_id, client_version, audit_writer)
    report = _lock_row(session, Report, report_id)
    _check_base(report, base_revision_number)

    payload = _report_payload(content)
    changed_fields = _changed_fields(report.current_content, payload)
    provenance = _ai_provenance(reason)
    revision = ReportRevision(
        report_id=report_id,
        revision_number=_next_revision_number(
            session, ReportRevision, ReportRevision.report_id, report_id),
        editor_account_id=actor.account_id,
        editor_staff_member_id=actor.staff_member_id,
        snapshot=payload,
        changed_fields=changed_fields,
        reason=reason,
        provenance=provenance,
        **{name: provenance.get(name) for name in PROVENANCE_COLUMN_NAMES},
        client_version=client_version,
        request_id=request_id,
    )
    session.add(revision)
    report.current_content = payload
    report.current_revision_number = revision.revision_number
    report.updated_at = datetime.now(UTC)
    _append_audit(
        session,
        audit_writer,
        actor,
        action="report.saved",
        target_type="report",
        target_id=report_id,
        request_id=request_id,
        details={
            "report_id": str(report_id),
            "revision_number": revision.revision_number,
            "changed_fields": changed_fields["fields"],
            "reason": reason,
        },
        client_version=client_version,
    )
    session.flush()
    return revision


def save_incident(
    session: Session,
    actor: Actor,
    incident_id: UUID,
    snapshot: IncidentSnapshotV1,
    base_revision_number: int,
    reason: str,
    *,
    request_id: str | None = None,
    client_version: str | None = None,
    audit_writer: AuditWriter | None = None,
) -> IncidentRevision:
    """Append and promote one validated incident revision in the caller transaction."""
    base_revision_number = _validate_revision_number(base_revision_number, "base")
    if reason not in INCIDENT_SAVE_REASONS:
        raise ValueError("incident revision reason is invalid")
    request_id, client_version, audit_writer = _metadata(
        request_id, client_version, audit_writer)
    incident = _lock_row(session, Incident, incident_id)
    _check_base(incident, base_revision_number)

    validated = IncidentSnapshotV1.model_validate(snapshot)
    payload = validated.model_dump(mode="json")
    changed_fields = _changed_fields(_incident_current_payload(incident), payload)
    persisted_snapshot = dict(payload)
    provenance = _ai_provenance(reason)
    if provenance:
        persisted_snapshot["provenance"] = provenance
    revision = IncidentRevision(
        incident_id=incident_id,
        revision_number=_next_revision_number(
            session, IncidentRevision, IncidentRevision.incident_id, incident_id),
        editor_account_id=actor.account_id,
        editor_staff_member_id=actor.staff_member_id,
        snapshot=persisted_snapshot,
        changed_fields=changed_fields,
        reason=reason,
        client_version=client_version,
        request_id=request_id,
    )
    session.add(revision)
    _apply_incident_snapshot(incident, validated, payload)
    incident.current_revision_number = revision.revision_number
    incident.updated_at = datetime.now(UTC)
    _append_audit(
        session,
        audit_writer,
        actor,
        action="incident.saved",
        target_type="incident",
        target_id=incident_id,
        request_id=request_id,
        details={
            "incident_id": str(incident_id),
            "revision_number": revision.revision_number,
            "changed_fields": changed_fields["fields"],
            "reason": reason,
        },
        client_version=client_version,
    )
    session.flush()
    return revision


def restore_report(
    session: Session,
    actor: Actor,
    report_id: UUID,
    revision_number: int,
    *,
    request_id: str | None = None,
    client_version: str | None = None,
    audit_writer: AuditWriter | None = None,
) -> ReportRevision:
    """Copy a historical snapshot forward and promote the new revision."""
    revision_number = _validate_revision_number(revision_number, "source")
    request_id, client_version, audit_writer = _metadata(
        request_id, client_version, audit_writer)
    report = _lock_row(session, Report, report_id)
    source = session.execute(select(ReportRevision).where(
        ReportRevision.report_id == report_id,
        ReportRevision.revision_number == revision_number,
    )).scalar_one_or_none()
    if source is None:
        raise RevisionTargetMissing("source revision was not found")

    payload = _report_payload(ReportContentV1.model_validate(source.snapshot))
    changed_fields = _changed_fields(report.current_content, payload)
    restored = ReportRevision(
        report_id=report_id,
        revision_number=_next_revision_number(
            session, ReportRevision, ReportRevision.report_id, report_id),
        editor_account_id=actor.account_id,
        editor_staff_member_id=actor.staff_member_id,
        snapshot=payload,
        changed_fields=changed_fields,
        reason="restored",
        provenance=_source_revision_provenance(source.provenance, revision_number),
        **{
            name: getattr(source, name)
            for name in PROVENANCE_COLUMN_NAMES
        },
        client_version=client_version,
        request_id=request_id,
    )
    session.add(restored)
    report.current_content = payload
    report.current_revision_number = restored.revision_number
    report.updated_at = datetime.now(UTC)
    _append_audit(
        session,
        audit_writer,
        actor,
        action="report.restored",
        target_type="report",
        target_id=report_id,
        request_id=request_id,
        details={
            "report_id": str(report_id),
            "revision_number": restored.revision_number,
            "source_revision_number": revision_number,
        },
        client_version=client_version,
    )
    session.flush()
    return restored


def create_recovery_revision(
    session: Session,
    actor: Actor,
    report_id: UUID,
    content: ReportContentV1,
    base_revision_number: int,
    *,
    request_id: str | None = None,
    client_version: str | None = None,
    audit_writer: AuditWriter | None = None,
) -> ReportRevision:
    """Append stale client content without promoting it over current content."""
    base_revision_number = _validate_revision_number(base_revision_number, "base")
    request_id, client_version, audit_writer = _metadata(
        request_id, client_version, audit_writer)
    report = _lock_row(session, Report, report_id)
    if base_revision_number > report.current_revision_number:
        raise RevisionTargetMissing("base revision was not found")
    source = session.execute(select(ReportRevision).where(
        ReportRevision.report_id == report_id,
        ReportRevision.revision_number == base_revision_number,
    )).scalar_one_or_none()
    if source is None:
        raise RevisionTargetMissing("base revision was not found")

    payload = _report_payload(content)
    changed_fields = _changed_fields(report.current_content, payload)
    recovery = ReportRevision(
        report_id=report_id,
        revision_number=_next_revision_number(
            session, ReportRevision, ReportRevision.report_id, report_id),
        editor_account_id=actor.account_id,
        editor_staff_member_id=actor.staff_member_id,
        snapshot=payload,
        changed_fields=changed_fields,
        reason="recovery",
        provenance=_source_revision_provenance(
            source.provenance, base_revision_number),
        **{
            name: getattr(source, name)
            for name in PROVENANCE_COLUMN_NAMES
        },
        client_version=client_version,
        request_id=request_id,
    )
    session.add(recovery)
    _append_audit(
        session,
        audit_writer,
        actor,
        action="report.recovery_created",
        target_type="report",
        target_id=report_id,
        request_id=request_id,
        details={
            "report_id": str(report_id),
            "revision_number": recovery.revision_number,
            "source_revision_number": base_revision_number,
        },
        client_version=client_version,
    )
    session.flush()
    return recovery
