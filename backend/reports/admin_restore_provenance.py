"""Preserve admin restore justification before immutable revision insertion."""
from copy import deepcopy
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.orm import Session

from backend.persistence.models.reporting import IncidentRevision


_SESSION_KEY = "admin_incident_restore_reason"
_PROVENANCE_KEY = "provenance"
_REASON_KEY = "admin_restore_reason"


def queue_admin_restore_reason(
    session: Session,
    *,
    incident_id: UUID,
    reason: str,
) -> None:
    """Queue trusted provenance for the next matching restored incident revision."""
    if not isinstance(incident_id, UUID):
        raise ValueError("incident id is invalid")
    if not isinstance(reason, str) or not reason:
        raise ValueError("restore reason is invalid")
    session.info[_SESSION_KEY] = (incident_id, reason)


@event.listens_for(Session, "before_flush")
def _attach_admin_restore_reason(session, _flush_context, _instances) -> None:
    pending = session.info.get(_SESSION_KEY)
    if pending is None:
        return
    incident_id, reason = pending
    for revision in tuple(session.new):
        if (
            isinstance(revision, IncidentRevision)
            and revision.incident_id == incident_id
            and revision.reason == "restored"
        ):
            snapshot = deepcopy(revision.snapshot)
            provenance = snapshot.get(_PROVENANCE_KEY)
            if not isinstance(provenance, dict):
                provenance = {}
            snapshot[_PROVENANCE_KEY] = {
                **provenance,
                _REASON_KEY: reason,
            }
            revision.snapshot = snapshot
            session.info.pop(_SESSION_KEY, None)
            return
