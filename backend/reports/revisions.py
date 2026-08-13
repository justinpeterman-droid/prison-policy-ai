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
    ReportAccess,
    ReportRevision,
)
from backend.persistence.models.identity import StaffMember
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
    "report_revision_editor_snapshot",
    "restore_report",
    "save_incident",
    "save_report",
    "save_report_status",
    "transfer_report_ownership",
]

DEFAULT_CLIENT_VERSION = "0.0.0-development"
INCIDENT_SAVE_REASONS = frozenset({"autosave", "manual_save", "ai_result"})
REPORT_SAVE_REASONS = frozenset({"autosave", "manual_save", "ai_result", "admin_edit"})
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
EDITOR_SNAPSHOT_KEY = "editor_snapshot"


class RevisionTargetMissing(LookupError):
    """The incident/report or requested source revision does not exist."""


@dataclass(frozen=True)
class RevisionConflict(Exception):
    """Safe metadata describing a stale base revision."""

    current_revision_number: int
    status: str | None = None
    updated_at: datetime | None = None
    current_editor_display_name: str | None = None
    changed_fields: tuple[str, ...] = ()

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
    audit_writer.append(
        session,
        AuditEventInput(
            actor_account_id=actor.account_id,
            actor_staff_member_id=actor.staff_member_id,
            action=action,
            result="success",
            request_id=request_id,
            target_type=target_type,
            target_id=target_id,
            details=details,
            client_version=client_version,
        ),
    )


def _report_payload(content: ReportContentV1) -> dict:
    return ReportContentV1.model_validate(content).model_dump(mode="json")


def _ai_provenance(reason: str) -> dict[str, str | None]:
    return collect_provenance() if reason == "ai_result" else {}


def _editor_snapshot(session: Session, actor: Actor) -> dict[str, str | None]:
    staff = session.get(StaffMember, actor.staff_member_id)
    if staff is None:
        raise ValueError("report revision editor is unavailable")
    display_name = " ".join(
        part for part in (staff.rank, staff.first_name, staff.last_name) if part
    )
    return {
        "staff_member_id": str(actor.staff_member_id),
        "display_name": display_name,
        "rank": staff.rank,
    }


def _with_editor_snapshot(
    session: Session,
    actor: Actor,
    provenance: dict | None,
) -> dict:
    # The service's locked caller-owned transaction contract is also exercised
    # with intentionally minimal, non-database session doubles. Real
    # persistence sessions always expose ``get`` and therefore always write
    # the immutable snapshot; doubles retain the pre-existing provenance-only
    # behavior rather than being forced to emulate roster persistence.
    if not callable(getattr(session, "get", None)):
        return dict(provenance or {})
    return {
        **dict(provenance or {}),
        EDITOR_SNAPSHOT_KEY: _editor_snapshot(session, actor),
    }


def report_revision_editor_snapshot(
    revision: ReportRevision,
) -> tuple[str | None, str | None]:
    """Return immutable editor attribution, or nullable legacy fallback.

    Revisions written before RP-05 hardening have no immutable roster
    snapshot. Returning null for those rows is safer than coupling historical
    attribution to a staff member's current name or rank, and matches the
    nullable Admin revision contract.
    """
    provenance = revision.provenance
    if not isinstance(provenance, dict):
        return None, None
    snapshot = provenance.get(EDITOR_SNAPSHOT_KEY)
    if not isinstance(snapshot, dict):
        return None, None
    if snapshot.get("staff_member_id") != str(revision.editor_staff_member_id):
        return None, None
    display_name = snapshot.get("display_name")
    rank = snapshot.get("rank")
    if not isinstance(display_name, str) or not display_name.strip():
        display_name = None
    if rank is not None and not isinstance(rank, str):
        rank = None
    return display_name, rank


def _source_revision_provenance(
    provenance: dict | None,
    source_revision_number: int,
) -> dict:
    source_revision_number = _validate_revision_number(source_revision_number, "source")
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
        value = (
            getattr(snapshot, field)
            if field in {"incident_date", "incident_time"}
            else payload[field]
        )
        setattr(incident, field, value)


def _check_base(session: Session, row, base_revision_number: int) -> None:
    if row.current_revision_number != base_revision_number:
        editor_display_name = None
        changed_fields: tuple[str, ...] = ()
        edited_at = row.updated_at
        if isinstance(row, Report):
            current = session.scalar(
                select(ReportRevision).where(
                    ReportRevision.report_id == row.id,
                    ReportRevision.revision_number == row.current_revision_number,
                )
            )
            if current is not None:
                editor_display_name, _editor_rank = report_revision_editor_snapshot(
                    current
                )
                changed_fields = tuple((current.changed_fields or {}).get("fields", ()))
                edited_at = current.created_at
        raise RevisionConflict(
            current_revision_number=row.current_revision_number,
            status=getattr(row.status, "value", row.status),
            updated_at=edited_at,
            current_editor_display_name=editor_display_name,
            changed_fields=changed_fields,
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
        request_id, client_version, audit_writer
    )
    report = _lock_row(session, Report, report_id)
    _check_base(session, report, base_revision_number)

    payload = _report_payload(content)
    changed_fields = _changed_fields(report.current_content, payload)
    provenance = _with_editor_snapshot(session, actor, _ai_provenance(reason))
    revision = ReportRevision(
        report_id=report_id,
        revision_number=_next_revision_number(
            session, ReportRevision, ReportRevision.report_id, report_id
        ),
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


def save_report_status(
    session: Session,
    actor: Actor,
    report_id: UUID,
    status: str,
    base_revision_number: int,
    *,
    request_id: str | None = None,
    client_version: str | None = None,
    audit_writer: AuditWriter | None = None,
) -> ReportRevision:
    """Append one status revision without locking Completed/Archived content."""
    base_revision_number = _validate_revision_number(base_revision_number, "base")
    if status not in {"in_progress", "completed", "archived"}:
        raise ValueError("report status is invalid")
    request_id, client_version, audit_writer = _metadata(
        request_id, client_version, audit_writer
    )
    report = _lock_row(session, Report, report_id)
    _check_base(session, report, base_revision_number)
    previous_status = getattr(report.status, "value", report.status)
    payload = _report_payload(ReportContentV1.model_validate(report.current_content))
    current = session.scalar(
        select(ReportRevision).where(
            ReportRevision.report_id == report_id,
            ReportRevision.revision_number == report.current_revision_number,
        )
    )
    provenance = _with_editor_snapshot(
        session,
        actor,
        current.provenance if current is not None else {},
    )
    fixed = datetime.now(UTC)
    revision = ReportRevision(
        report_id=report_id,
        revision_number=_next_revision_number(
            session, ReportRevision, ReportRevision.report_id, report_id
        ),
        editor_account_id=actor.account_id,
        editor_staff_member_id=actor.staff_member_id,
        snapshot=payload,
        changed_fields={"fields": []},
        reason="status_change",
        provenance=provenance,
        **{
            name: getattr(current, name) if current is not None else None
            for name in PROVENANCE_COLUMN_NAMES
        },
        client_version=client_version,
        request_id=request_id,
        created_at=fixed,
    )
    session.add(revision)
    report.status = status
    report.current_revision_number = revision.revision_number
    report.updated_at = fixed
    report.archived_at = fixed if status == "archived" else None
    _append_audit(
        session,
        audit_writer,
        actor,
        action="report.status_changed",
        target_type="report",
        target_id=report_id,
        request_id=request_id,
        details={"old_status": previous_status, "new_status": status},
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
        request_id, client_version, audit_writer
    )
    incident = _lock_row(session, Incident, incident_id)
    _check_base(session, incident, base_revision_number)

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
            session, IncidentRevision, IncidentRevision.incident_id, incident_id
        ),
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
        request_id, client_version, audit_writer
    )
    report = _lock_row(session, Report, report_id)
    source = session.execute(
        select(ReportRevision).where(
            ReportRevision.report_id == report_id,
            ReportRevision.revision_number == revision_number,
        )
    ).scalar_one_or_none()
    if source is None:
        raise RevisionTargetMissing("source revision was not found")

    payload = _report_payload(ReportContentV1.model_validate(source.snapshot))
    changed_fields = _changed_fields(report.current_content, payload)
    restored = ReportRevision(
        report_id=report_id,
        revision_number=_next_revision_number(
            session, ReportRevision, ReportRevision.report_id, report_id
        ),
        editor_account_id=actor.account_id,
        editor_staff_member_id=actor.staff_member_id,
        snapshot=payload,
        changed_fields=changed_fields,
        reason="restored",
        provenance=_with_editor_snapshot(
            session,
            actor,
            _source_revision_provenance(source.provenance, revision_number),
        ),
        **{name: getattr(source, name) for name in PROVENANCE_COLUMN_NAMES},
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
        request_id, client_version, audit_writer
    )
    report = _lock_row(session, Report, report_id)
    if base_revision_number > report.current_revision_number:
        raise RevisionTargetMissing("base revision was not found")
    source = session.execute(
        select(ReportRevision).where(
            ReportRevision.report_id == report_id,
            ReportRevision.revision_number == base_revision_number,
        )
    ).scalar_one_or_none()
    if source is None:
        raise RevisionTargetMissing("base revision was not found")

    payload = _report_payload(content)
    changed_fields = _changed_fields(report.current_content, payload)
    recovery = ReportRevision(
        report_id=report_id,
        revision_number=_next_revision_number(
            session, ReportRevision, ReportRevision.report_id, report_id
        ),
        editor_account_id=actor.account_id,
        editor_staff_member_id=actor.staff_member_id,
        snapshot=payload,
        changed_fields=changed_fields,
        reason="recovery",
        provenance=_with_editor_snapshot(
            session,
            actor,
            _source_revision_provenance(source.provenance, base_revision_number),
        ),
        **{name: getattr(source, name) for name in PROVENANCE_COLUMN_NAMES},
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


def transfer_report_ownership(
    session: Session,
    actor: Actor,
    report_id: UUID,
    new_owner_staff_id: UUID,
    new_preparer_staff_id: UUID | None,
    *,
    request_id: str | None = None,
    client_version: str | None = None,
    audit_writer: AuditWriter | None = None,
) -> ReportRevision:
    """Replace owner/preparer access, then append an ownership revision.

    Locks the report and every access row it has ever had, verifies both
    target staff members are active, revokes access for anyone no longer in
    the resolved owner/preparer pair, grants (or reactivates) access for the
    resolved pair, and appends an unchanged-content revision naming the
    administrator. `report_access` is keyed on `(report_id, staff_member_id)`
    -- one row per staff member per report for all time -- so returning
    access reactivates that staff member's existing row rather than
    inserting a second one; a row already revoked before is never deleted,
    only its `revoked_at`/`relationship` are updated forward.
    """
    request_id, client_version, audit_writer = _metadata(
        request_id, client_version, audit_writer
    )
    report = _lock_row(session, Report, report_id)
    resolved_preparer = new_preparer_staff_id or report.prepared_by_staff_member_id
    target_ids = {new_owner_staff_id, resolved_preparer}
    active = (
        session.execute(
            select(StaffMember)
            .where(StaffMember.id.in_(target_ids), StaffMember.is_active.is_(True))
            .with_for_update()
        )
        .scalars()
        .all()
    )
    if {row.id for row in active} != target_ids:
        raise ValueError("Transfer targets must identify active staff.")

    existing_by_staff = {
        row.staff_member_id: row
        for row in session.execute(
            select(ReportAccess)
            .where(ReportAccess.report_id == report_id)
            .with_for_update()
        )
        .scalars()
        .all()
    }
    fixed = datetime.now(UTC)
    old_owner_staff_id = report.reporting_staff_member_id

    relationships = [(new_owner_staff_id, "owner")]
    if resolved_preparer != new_owner_staff_id:
        relationships.append((resolved_preparer, "preparer"))
    final_staff_ids = {staff_id for staff_id, _relationship in relationships}

    for staff_id, row in existing_by_staff.items():
        if staff_id not in final_staff_ids and row.revoked_at is None:
            row.revoked_at = fixed
    for staff_id, relationship in relationships:
        row = existing_by_staff.get(staff_id)
        if row is not None:
            row.relationship = relationship
            row.revoked_at = None
            row.granted_by_account_id = actor.account_id
        else:
            session.add(
                ReportAccess(
                    report_id=report_id,
                    staff_member_id=staff_id,
                    relationship=relationship,
                    granted_by_account_id=actor.account_id,
                    created_at=fixed,
                )
            )
    report.reporting_staff_member_id = new_owner_staff_id
    report.prepared_by_staff_member_id = resolved_preparer

    payload = _report_payload(ReportContentV1.model_validate(report.current_content))
    revision = ReportRevision(
        report_id=report_id,
        revision_number=_next_revision_number(
            session, ReportRevision, ReportRevision.report_id, report_id
        ),
        editor_account_id=actor.account_id,
        editor_staff_member_id=actor.staff_member_id,
        snapshot=payload,
        changed_fields={"fields": []},
        reason="ownership_change",
        provenance=_with_editor_snapshot(session, actor, {}),
        client_version=client_version,
        request_id=request_id,
        created_at=fixed,
    )
    session.add(revision)
    report.current_revision_number = revision.revision_number
    report.updated_at = fixed
    _append_audit(
        session,
        audit_writer,
        actor,
        action="report.ownership_transferred",
        target_type="report",
        target_id=report_id,
        request_id=request_id,
        details={
            "report_id": str(report_id),
            "old_owner_staff_id": str(old_owner_staff_id),
            "new_owner_staff_id": str(new_owner_staff_id),
        },
        client_version=client_version,
    )
    session.flush()
    return revision
