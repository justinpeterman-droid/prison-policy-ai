"""Keep official incident identity synchronized across every revision write path."""
from sqlalchemy import event
from sqlalchemy.orm import Session

from backend.persistence.models.reporting import Incident, IncidentRevision


IDENTITY_FIELDS = ("incident_number", "incident_name")
AI_REVISION_REASON = "ai_result"


def _incident_for_revision(
    session: Session, revision: IncidentRevision,
) -> Incident | None:
    for pending in session.new:
        if isinstance(pending, Incident) and pending.id == revision.incident_id:
            return pending
    return session.get(Incident, revision.incident_id)


@event.listens_for(Session, "before_flush")
def synchronize_incident_identity(
    session: Session, _flush_context, _instances,
) -> None:
    """Promote revisioned identity and prevent AI revisions from changing it."""
    for revision in tuple(session.new):
        if not isinstance(revision, IncidentRevision):
            continue
        if not isinstance(revision.snapshot, dict):
            continue

        incident = _incident_for_revision(session, revision)
        if incident is None:
            continue

        snapshot = dict(revision.snapshot)
        reason = getattr(revision.reason, "value", revision.reason)
        desired = {
            field: (
                getattr(incident, field)
                if reason == AI_REVISION_REASON
                else snapshot.get(field)
            )
            for field in IDENTITY_FIELDS
        }

        changed_fields = dict(revision.changed_fields or {})
        field_names = set(changed_fields.get("fields", ()))
        for field, value in desired.items():
            field_names.discard(field)
            if getattr(incident, field) != value:
                field_names.add(field)
            snapshot[field] = value
            setattr(incident, field, value)

        revision.snapshot = snapshot
        changed_fields["fields"] = sorted(field_names)
        revision.changed_fields = changed_fields
