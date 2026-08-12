"""Authorized, caller-transaction-owned incident persistence operations."""
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.identity.audit import AuditEventInput, AuditWriter, PostgresAuditWriter
from backend.identity.idempotency import (
    claim_idempotency,
    complete_idempotency,
    request_digest,
)
from backend.persistence.models.identity import StaffMember
from backend.persistence.models.reporting import (
    Incident,
    IncidentRevision,
    Report,
    ReportAccess,
)
from backend.reports.revisions import RevisionConflict
from backend.webapp.api_v1.middleware import Actor
from backend.webapp.api_v1.schemas.reporting import (
    IncidentSnapshotV1,
    SaveIncidentRequest,
    changed_field_names,
)


SERVER_METADATA_KEY = "server_metadata"
REPORTING_STAFF_IDS_KEY = "reporting_staff_ids"
MAX_REPORTING_STAFF = 20


class IncidentNotFound(LookupError):
    pass


class IncidentRevisionNotFound(LookupError):
    pass


@dataclass(frozen=True)
class IncidentView:
    incident: Incident
    reporting_staff_ids: tuple[UUID, ...]


def _content_payload(value: IncidentSnapshotV1 | SaveIncidentRequest) -> dict:
    if isinstance(value, SaveIncidentRequest):
        value = IncidentSnapshotV1.model_validate(value.model_dump(
            exclude={"base_revision_number", "reason"}))
    return IncidentSnapshotV1.model_validate(value).model_dump(mode="json")


def _server_snapshot(content: dict, reporting_staff_ids: tuple[UUID, ...]) -> dict:
    return {
        **content,
        SERVER_METADATA_KEY: {
            REPORTING_STAFF_IDS_KEY: [str(staff_id) for staff_id in reporting_staff_ids],
        },
    }


def _selection_from_snapshot(snapshot: dict) -> tuple[UUID, ...]:
    metadata = snapshot.get(SERVER_METADATA_KEY, {})
    values = metadata.get(REPORTING_STAFF_IDS_KEY, []) if isinstance(metadata, dict) else []
    if not isinstance(values, list):
        raise RuntimeError("incident server metadata is invalid")
    try:
        return tuple(UUID(value) for value in values)
    except (TypeError, ValueError):
        raise RuntimeError("incident server metadata is invalid") from None


def _latest_revision(session: Session, incident_id: UUID) -> IncidentRevision:
    revision = session.scalar(
        select(IncidentRevision)
        .where(IncidentRevision.incident_id == incident_id)
        .order_by(IncidentRevision.revision_number.desc())
        .limit(1)
    )
    if revision is None:
        raise IncidentNotFound("Incident not found.")
    return revision


def _active_selection(session: Session, values: object) -> tuple[UUID, ...]:
    if not isinstance(values, list) or not 1 <= len(values) <= MAX_REPORTING_STAFF:
        raise ValueError("reporting_staff_ids must contain 1 through 20 staff UUIDs")
    normalized = []
    seen = set()
    for value in values:
        if not isinstance(value, (str, UUID)):
            raise ValueError("reporting_staff_ids must contain staff UUIDs")
        try:
            staff_id = value if isinstance(value, UUID) else UUID(value)
        except ValueError:
            raise ValueError("reporting_staff_ids must contain staff UUIDs") from None
        if staff_id not in seen:
            normalized.append(staff_id)
            seen.add(staff_id)
    rows = session.scalars(select(StaffMember).where(
        StaffMember.id.in_(normalized), StaffMember.is_active.is_(True),
    )).all()
    if {row.id for row in rows} != set(normalized):
        raise ValueError("Every reporting staff ID must identify active staff.")
    return tuple(normalized)


def _can_access_incident(
    session: Session, actor: Actor, incident: Incident, reporting_staff_ids: tuple[UUID, ...],
) -> bool:
    if actor.role == "admin":
        return True
    if actor.staff_member_id == incident.created_by_staff_member_id:
        return True
    if actor.staff_member_id in reporting_staff_ids:
        return True
    live_relationship = session.scalar(
        select(ReportAccess.report_id)
        .join(Report, Report.id == ReportAccess.report_id)
        .where(
            Report.incident_id == incident.id,
            ReportAccess.staff_member_id == actor.staff_member_id,
            ReportAccess.revoked_at.is_(None),
        )
        .limit(1)
    )
    return live_relationship is not None


def get_incident(session: Session, actor: Actor, incident_id: UUID) -> IncidentView:
    incident = session.get(Incident, incident_id)
    if incident is None:
        raise IncidentNotFound("Incident not found.")
    reporting_staff_ids = _selection_from_snapshot(
        _latest_revision(session, incident_id).snapshot)
    if not _can_access_incident(session, actor, incident, reporting_staff_ids):
        raise IncidentNotFound("Incident not found.")
    return IncidentView(incident, reporting_staff_ids)


def _append_audit(
    session: Session, audit_writer: AuditWriter, actor: Actor, *, action: str,
    incident_id: UUID, request_id: str, client_version: str, details: dict,
) -> None:
    audit_writer.append(session, AuditEventInput(
        actor_account_id=actor.account_id,
        actor_staff_member_id=actor.staff_member_id,
        action=action,
        result="success",
        request_id=request_id,
        target_type="incident",
        target_id=incident_id,
        details=details,
        client_version=client_version,
    ))


def _apply_content(incident: Incident, validated: IncidentSnapshotV1, payload: dict) -> None:
    for field in (
        "incident_date", "incident_time", "facility", "shift", "location", "category",
        "field_notes", "classification", "extracted_facts", "gap_answers", "charges",
        "validation",
    ):
        setattr(
            incident, field,
            getattr(validated, field) if field in {"incident_date", "incident_time"} else payload[field],
        )


def _view_from_reference(session: Session, actor: Actor, reference: dict) -> IncidentView:
    try:
        incident_id = UUID(str(reference["incident_id"]))
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("idempotency reference is invalid") from None
    return get_incident(session, actor, incident_id)


def create_incident(
    session: Session,
    actor: Actor,
    reporting_staff_ids: list[str | UUID],
    request_model: SaveIncidentRequest,
    idempotency_key: str,
    *,
    now: datetime | None = None,
    request_id: str,
    client_version: str,
    audit_writer: AuditWriter | None = None,
) -> IncidentView:
    """Create revision one, idempotency completion, and audit in one transaction."""
    validated = SaveIncidentRequest.model_validate(request_model)
    if validated.base_revision_number != 0:
        raise ValueError("A new incident must use base_revision_number 0.")
    selection = _active_selection(session, reporting_staff_ids)
    content = _content_payload(validated)
    canonical = {
        "reporting_staff_ids": [str(value) for value in selection],
        "content": content,
    }
    fixed = now or datetime.now(UTC)
    claim = claim_idempotency(
        session, actor, key=idempotency_key, action="incident.create",
        request_sha256=request_digest(canonical), now=fixed,
    )
    if claim.replayed:
        return _view_from_reference(session, actor, claim.response_reference or {})

    incident = Incident(
        id=uuid4(),
        created_by_account_id=actor.account_id,
        created_by_staff_member_id=actor.staff_member_id,
        status="in_progress",
        current_revision_number=1,
        created_at=fixed,
        updated_at=fixed,
    )
    _apply_content(incident, IncidentSnapshotV1.model_validate(content), content)
    session.add(incident)
    revision = IncidentRevision(
        id=uuid4(),
        incident_id=incident.id,
        revision_number=1,
        editor_account_id=actor.account_id,
        editor_staff_member_id=actor.staff_member_id,
        snapshot=_server_snapshot(content, selection),
        changed_fields={"fields": ["field_notes"] if content.get("field_notes") else []},
        reason="manual_save",
        client_version=client_version,
        request_id=request_id,
        created_at=fixed,
    )
    session.add(revision)
    writer = audit_writer or PostgresAuditWriter()
    _append_audit(
        session, writer, actor, action="incident.created", incident_id=incident.id,
        request_id=request_id, client_version=client_version,
        details={"incident_id": str(incident.id)},
    )
    complete_idempotency(
        session, claim, response_status=201,
        response_reference={"incident_id": str(incident.id)}, now=fixed,
    )
    session.flush()
    return IncidentView(incident, selection)


def save_incident_record(
    session: Session, actor: Actor, incident_id: UUID,
    request_model: SaveIncidentRequest, idempotency_key: str, *,
    now: datetime | None = None, request_id: str, client_version: str,
    audit_writer: AuditWriter | None = None,
) -> IncidentView:
    validated = SaveIncidentRequest.model_validate(request_model)
    current = get_incident(session, actor, incident_id)
    fixed = now or datetime.now(UTC)
    canonical = {"incident_id": str(incident_id), **validated.model_dump(mode="json")}
    claim = claim_idempotency(
        session, actor, key=idempotency_key, action="incident.save",
        request_sha256=request_digest(canonical), now=fixed,
    )
    if claim.replayed:
        return _view_from_reference(session, actor, claim.response_reference or {})
    content = IncidentSnapshotV1.model_validate(validated.model_dump(
        exclude={"base_revision_number", "reason"}))
    incident = session.scalar(select(Incident).where(
        Incident.id == incident_id).with_for_update())
    if incident is None:
        raise IncidentNotFound("Incident not found.")
    if incident.current_revision_number != validated.base_revision_number:
        raise RevisionConflict(
            current_revision_number=incident.current_revision_number,
            status=incident.status,
            updated_at=incident.updated_at,
        )
    payload = _content_payload(content)
    previous = IncidentSnapshotV1.model_validate({
        field: getattr(incident, field)
        for field in (
            "incident_date", "incident_time", "facility", "shift", "location", "category",
            "field_notes", "classification", "extracted_facts", "gap_answers", "charges",
            "validation",
        )
    }).model_dump(mode="json")
    next_number = incident.current_revision_number + 1
    revision = IncidentRevision(
        id=uuid4(), incident_id=incident_id, revision_number=next_number,
        editor_account_id=actor.account_id,
        editor_staff_member_id=actor.staff_member_id,
        snapshot=_server_snapshot(payload, current.reporting_staff_ids),
        changed_fields={"fields": changed_field_names(previous, payload)},
        reason=validated.reason,
        client_version=client_version,
        request_id=request_id,
        created_at=fixed,
    )
    session.add(revision)
    _apply_content(incident, content, payload)
    incident.current_revision_number = next_number
    incident.updated_at = fixed
    writer = audit_writer or PostgresAuditWriter()
    _append_audit(
        session, writer, actor, action="incident.saved", incident_id=incident_id,
        request_id=request_id, client_version=client_version,
        details={
            "incident_id": str(incident_id), "revision_number": next_number,
            "changed_fields": revision.changed_fields["fields"],
            "reason": validated.reason,
        },
    )
    complete_idempotency(
        session, claim, response_status=200,
        response_reference={"incident_id": str(incident_id)}, now=fixed,
    )
    session.flush()
    return IncidentView(incident, current.reporting_staff_ids)


def list_incident_revisions(
    session: Session, actor: Actor, incident_id: UUID,
) -> list[IncidentRevision]:
    get_incident(session, actor, incident_id)
    return list(session.scalars(select(IncidentRevision).where(
        IncidentRevision.incident_id == incident_id,
    ).order_by(IncidentRevision.revision_number)).all())


def get_incident_revision(
    session: Session, actor: Actor, incident_id: UUID, revision_number: int,
) -> IncidentRevision:
    get_incident(session, actor, incident_id)
    revision = session.scalar(select(IncidentRevision).where(
        IncidentRevision.incident_id == incident_id,
        IncidentRevision.revision_number == revision_number,
    ))
    if revision is None:
        raise IncidentRevisionNotFound("Incident revision not found.")
    return revision


def restore_incident_record(
    session: Session, actor: Actor, incident_id: UUID, revision_number: int,
    idempotency_key: str, *, now: datetime | None = None, request_id: str,
    client_version: str, audit_writer: AuditWriter | None = None,
) -> IncidentView:
    if not isinstance(revision_number, int) or isinstance(revision_number, bool) or revision_number < 1:
        raise ValueError("revision_number must be a positive integer")
    current = get_incident(session, actor, incident_id)
    fixed = now or datetime.now(UTC)
    canonical = {"incident_id": str(incident_id), "revision_number": revision_number}
    claim = claim_idempotency(
        session, actor, key=idempotency_key, action="incident.restore",
        request_sha256=request_digest(canonical), now=fixed,
    )
    if claim.replayed:
        return _view_from_reference(session, actor, claim.response_reference or {})
    incident = session.scalar(select(Incident).where(
        Incident.id == incident_id).with_for_update())
    if incident is None:
        raise IncidentNotFound("Incident not found.")
    source = get_incident_revision(session, actor, incident_id, revision_number)
    source_content = {
        key: value for key, value in source.snapshot.items() if key != SERVER_METADATA_KEY
    }
    validated = IncidentSnapshotV1.model_validate(source_content)
    payload = validated.model_dump(mode="json")
    previous = IncidentSnapshotV1.model_validate({
        field: getattr(incident, field)
        for field in (
            "incident_date", "incident_time", "facility", "shift", "location", "category",
            "field_notes", "classification", "extracted_facts", "gap_answers", "charges",
            "validation",
        )
    }).model_dump(mode="json")
    next_number = incident.current_revision_number + 1
    restored = IncidentRevision(
        id=uuid4(), incident_id=incident_id, revision_number=next_number,
        editor_account_id=actor.account_id, editor_staff_member_id=actor.staff_member_id,
        snapshot=_server_snapshot(payload, current.reporting_staff_ids),
        changed_fields={"fields": changed_field_names(previous, payload)},
        reason="restored", client_version=client_version, request_id=request_id,
        created_at=fixed,
    )
    session.add(restored)
    _apply_content(incident, validated, payload)
    incident.current_revision_number = next_number
    incident.updated_at = fixed
    writer = audit_writer or PostgresAuditWriter()
    _append_audit(
        session, writer, actor, action="incident.restored", incident_id=incident_id,
        request_id=request_id, client_version=client_version,
        details={
            "incident_id": str(incident_id), "revision_number": next_number,
            "source_revision_number": revision_number,
        },
    )
    complete_idempotency(
        session, claim, response_status=200,
        response_reference={"incident_id": str(incident_id)}, now=fixed,
    )
    session.flush()
    return IncidentView(incident, current.reporting_staff_ids)


def incident_revision_content(revision: IncidentRevision) -> dict:
    return {
        key: value for key, value in revision.snapshot.items()
        if key != SERVER_METADATA_KEY
    }


__all__ = [
    "IncidentNotFound", "IncidentRevisionNotFound", "IncidentView",
    "create_incident", "get_incident", "get_incident_revision",
    "incident_revision_content", "list_incident_revisions",
    "restore_incident_record", "save_incident_record",
]
