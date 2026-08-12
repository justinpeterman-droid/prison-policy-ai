"""Row-locked, one-transaction save/restore/recovery for incidents and reports.

Two officers editing the same report is the normal case, not the exotic one: a
preparer types while the reporting officer reviews. The rule this module exists
to enforce is that a save from a stale base revision *fails loudly* instead of
overwriting work someone else already saved.

Every operation is one transaction. The report row is locked `FOR UPDATE`, the
base revision is compared under that lock, the immutable snapshot is appended,
the current row is updated, and the audit event is written — then one commit.
If any step raises, the whole thing rolls back, so there is never a revision
without its audit row or an audit row without its revision.
"""
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.identity.audit import AuditEventInput, AuditWriter
from backend.persistence.models.reporting import (
    Incident,
    IncidentRevision,
    Report,
    ReportRevision,
)
from backend.webapp.api_v1.middleware import Actor
from backend.webapp.api_v1.schemas.reporting import (
    IncidentSnapshotV1,
    ReportContentV1,
    RevisionSummary,
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


class RevisionTargetMissing(LookupError):
    """The incident or report does not exist (or is concealed from this actor)."""


@dataclass(frozen=True)
class RevisionConflict(Exception):
    """A save was attempted from a revision that is no longer current.

    Carries only what the client needs to recover — the current revision
    number, status, and modification time. Never the content that won, which
    the client must re-read through the normal access-checked path.
    """

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
    """One past the highest revision ever written for this parent.

    Deliberately not `current_revision_number + 1`: a recovery revision is
    appended to history without being promoted to current, and the next real
    save must still land on an unused number.
    """
    highest = session.execute(
        select(func.max(model.revision_number)).where(column == parent_id)
    ).scalar()
    return (highest or 0) + 1


def _summary(revision, changed: list[str], client_version: str | None) -> RevisionSummary:
    return RevisionSummary(
        revision_number=revision.revision_number,
        reason=revision.reason,
        changed_fields=changed,
        created_at=revision.created_at or datetime.now(UTC),
        editor_staff_member_id=revision.editor_staff_member_id,
        source_revision_number=getattr(revision, "source_revision_number", None),
        client_version=client_version,
    )


def _append_audit(
    session: Session,
    audit: AuditWriter,
    actor: Actor,
    *,
    action: str,
    target_type: str,
    target_id: UUID,
    request_id: str,
    details: dict,
    client_version: str | None,
) -> None:
    audit.append(session, AuditEventInput(
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


def save_report(
    session: Session,
    actor: Actor,
    report_id: UUID,
    content: ReportContentV1,
    *,
    base_revision_number: int,
    reason: str = "manual_save",
    request_id: str,
    audit: AuditWriter,
    client_version: str | None = None,
) -> RevisionSummary:
    """Append one report revision, or raise `RevisionConflict`."""
    with session.begin():
        report = _lock_row(session, Report, report_id)
        if report.current_revision_number != base_revision_number:
            raise RevisionConflict(
                current_revision_number=report.current_revision_number,
                status=getattr(report.status, "value", report.status),
                updated_at=report.updated_at,
            )

        payload = ReportContentV1.model_validate(content).model_dump(mode="json")
        changed = changed_field_names(report.content, payload)
        revision_number = _next_revision_number(
            session, ReportRevision, ReportRevision.report_id, report_id)

        session.add(ReportRevision(
            report_id=report_id,
            revision_number=revision_number,
            editor_account_id=actor.account_id,
            editor_staff_member_id=actor.staff_member_id,
            snapshot=payload,
            changed_fields=changed,
            reason=reason,
            client_version=client_version,
            request_id=request_id,
        ))
        report.content = payload
        report.current_revision_number = revision_number
        report.updated_at = datetime.now(UTC)

        _append_audit(
            session, audit, actor,
            action="report.saved",
            target_type="report",
            target_id=report_id,
            request_id=request_id,
            details={
                "report_id": str(report_id),
                "revision_number": revision_number,
                "changed_fields": changed,
                "reason": reason,
            },
            client_version=client_version,
        )

    revision = session.execute(
        select(ReportRevision).where(
            ReportRevision.report_id == report_id,
            ReportRevision.revision_number == revision_number,
        )
    ).scalar_one()
    return _summary(revision, changed, client_version)


def save_incident(
    session: Session,
    actor: Actor,
    incident_id: UUID,
    snapshot: IncidentSnapshotV1,
    *,
    base_revision_number: int,
    reason: str = "manual_save",
    request_id: str,
    audit: AuditWriter,
    client_version: str | None = None,
) -> RevisionSummary:
    """Append one incident revision, or raise `RevisionConflict`."""
    with session.begin():
        incident = _lock_row(session, Incident, incident_id)
        if incident.current_revision_number != base_revision_number:
            raise RevisionConflict(
                current_revision_number=incident.current_revision_number,
                status=getattr(incident.status, "value", incident.status),
                updated_at=incident.updated_at,
            )

        payload = IncidentSnapshotV1.model_validate(snapshot).model_dump(mode="json")
        changed = changed_field_names(incident.snapshot, payload)
        revision_number = _next_revision_number(
            session, IncidentRevision, IncidentRevision.incident_id, incident_id)

        session.add(IncidentRevision(
            incident_id=incident_id,
            revision_number=revision_number,
            editor_account_id=actor.account_id,
            editor_staff_member_id=actor.staff_member_id,
            snapshot=payload,
            changed_fields=changed,
            reason=reason,
            client_version=client_version,
            request_id=request_id,
        ))
        incident.snapshot = payload
        incident.current_revision_number = revision_number
        incident.updated_at = datetime.now(UTC)

        _append_audit(
            session, audit, actor,
            action="incident.saved",
            target_type="incident",
            target_id=incident_id,
            request_id=request_id,
            details={
                "incident_id": str(incident_id),
                "revision_number": revision_number,
                "changed_fields": changed,
                "reason": reason,
            },
            client_version=client_version,
        )

    revision = session.execute(
        select(IncidentRevision).where(
            IncidentRevision.incident_id == incident_id,
            IncidentRevision.revision_number == revision_number,
        )
    ).scalar_one()
    return _summary(revision, changed, client_version)


def restore_report(
    session: Session,
    actor: Actor,
    report_id: UUID,
    *,
    source_revision_number: int,
    base_revision_number: int,
    request_id: str,
    audit: AuditWriter,
    client_version: str | None = None,
) -> RevisionSummary:
    """Copy a historical snapshot forward as a new current revision.

    History is never rewritten: restoring revision 1 over revision 4 writes
    revision 5 whose content equals revision 1's, so the fact that a restore
    happened stays visible.
    """
    with session.begin():
        report = _lock_row(session, Report, report_id)
        if report.current_revision_number != base_revision_number:
            raise RevisionConflict(
                current_revision_number=report.current_revision_number,
                status=getattr(report.status, "value", report.status),
                updated_at=report.updated_at,
            )

        source = session.execute(
            select(ReportRevision).where(
                ReportRevision.report_id == report_id,
                ReportRevision.revision_number == source_revision_number,
            )
        ).scalar_one_or_none()
        if source is None:
            raise RevisionTargetMissing("source revision was not found")

        payload = ReportContentV1.model_validate(source.snapshot).model_dump(
            mode="json")
        changed = changed_field_names(report.content, payload)
        revision_number = _next_revision_number(
            session, ReportRevision, ReportRevision.report_id, report_id)

        session.add(ReportRevision(
            report_id=report_id,
            revision_number=revision_number,
            editor_account_id=actor.account_id,
            editor_staff_member_id=actor.staff_member_id,
            snapshot=payload,
            changed_fields=changed,
            reason="restored",
            source_revision_number=source_revision_number,
            client_version=client_version,
            request_id=request_id,
        ))
        report.content = payload
        report.current_revision_number = revision_number
        report.updated_at = datetime.now(UTC)

        _append_audit(
            session, audit, actor,
            action="report.restored",
            target_type="report",
            target_id=report_id,
            request_id=request_id,
            details={
                "report_id": str(report_id),
                "revision_number": revision_number,
                "source_revision_number": source_revision_number,
            },
            client_version=client_version,
        )

    revision = session.execute(
        select(ReportRevision).where(
            ReportRevision.report_id == report_id,
            ReportRevision.revision_number == revision_number,
        )
    ).scalar_one()
    return _summary(revision, changed, client_version)


def create_recovery_revision(
    session: Session,
    actor: Actor,
    report_id: UUID,
    content: ReportContentV1,
    *,
    request_id: str,
    audit: AuditWriter,
    client_version: str | None = None,
) -> RevisionSummary:
    """Preserve unsaved client content without promoting it over the current.

    A client that crashed mid-edit has content nobody else has seen. Losing it
    is bad; silently making it current is worse, because whoever saved in the
    meantime would have their work replaced by a draft they never saw. So the
    recovery lands in history and the officer is shown both.
    """
    with session.begin():
        report = _lock_row(session, Report, report_id)
        payload = ReportContentV1.model_validate(content).model_dump(mode="json")
        changed = changed_field_names(report.content, payload)
        revision_number = _next_revision_number(
            session, ReportRevision, ReportRevision.report_id, report_id)

        session.add(ReportRevision(
            report_id=report_id,
            revision_number=revision_number,
            editor_account_id=actor.account_id,
            editor_staff_member_id=actor.staff_member_id,
            snapshot=payload,
            changed_fields=changed,
            reason="recovery",
            source_revision_number=report.current_revision_number,
            client_version=client_version,
            request_id=request_id,
        ))
        # Deliberately no promotion: `current_revision_number` and `content`
        # keep pointing at whatever was last actually saved.

        _append_audit(
            session, audit, actor,
            action="report.recovery_created",
            target_type="report",
            target_id=report_id,
            request_id=request_id,
            details={
                "report_id": str(report_id),
                "revision_number": revision_number,
                "source_revision_number": report.current_revision_number,
            },
            client_version=client_version,
        )

    revision = session.execute(
        select(ReportRevision).where(
            ReportRevision.report_id == report_id,
            ReportRevision.revision_number == revision_number,
        )
    ).scalar_one()
    return _summary(revision, changed, client_version)
