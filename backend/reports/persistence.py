"""Authorized, caller-transaction-owned incident persistence operations."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from uuid import UUID, uuid4

from sqlalchemy import and_, event, or_, select
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
    revision_number: int | None = None
    status: str | None = None
    content: dict | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class IncidentRevisionPage:
    items: list[IncidentRevision]
    next_cursor: dict[str, str] | None


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


def _content_from_snapshot(snapshot: dict) -> dict:
    content = {
        key: value for key, value in snapshot.items()
        if key not in {SERVER_METADATA_KEY, "provenance"}
    }
    return IncidentSnapshotV1.model_validate_json(
        json.dumps(content)).model_dump(mode="json")


@event.listens_for(Session, "before_flush")
def _carry_incident_server_metadata(session, _flush_context, _instances) -> None:
    """Carry trusted selection metadata into revisions written by RP-02 services."""
    for revision in tuple(session.new):
        if not isinstance(revision, IncidentRevision):
            continue
        snapshot = revision.snapshot
        if not isinstance(snapshot, dict) or SERVER_METADATA_KEY in snapshot:
            continue
        previous = session.scalar(
            select(IncidentRevision)
            .where(
                IncidentRevision.incident_id == revision.incident_id,
                IncidentRevision.snapshot.has_key(SERVER_METADATA_KEY),  # noqa: W601
            )
            .order_by(
                IncidentRevision.revision_number.desc(), IncidentRevision.id.desc())
            .limit(1)
        )
        if previous is not None:
            revision.snapshot = {
                **snapshot,
                SERVER_METADATA_KEY: deepcopy(previous.snapshot[SERVER_METADATA_KEY]),
            }


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


def _normalize_selection(values: object) -> tuple[UUID, ...]:
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
    return tuple(normalized)


def _active_selection(session: Session, normalized: tuple[UUID, ...]) -> tuple[UUID, ...]:
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
        revision_number = int(reference["revision_number"])
        reporting_staff_ids = tuple(
            UUID(str(value)) for value in reference["reporting_staff_ids"])
        status = str(reference["status"])
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("idempotency reference is invalid") from None
    incident = session.get(Incident, incident_id)
    revision = session.scalar(select(IncidentRevision).where(
        IncidentRevision.incident_id == incident_id,
        IncidentRevision.revision_number == revision_number,
    ))
    if incident is None or revision is None:
        raise RuntimeError("idempotency reference is invalid")
    return IncidentView(
        incident,
        reporting_staff_ids,
        revision_number=revision_number,
        status=status,
        content=_content_from_snapshot(revision.snapshot),
        updated_at=revision.created_at,
    )


def _response_reference(view: IncidentView) -> dict[str, object]:
    return {
        "incident_id": str(view.incident.id),
        "revision_number": view.revision_number or view.incident.current_revision_number,
        "reporting_staff_ids": [str(value) for value in view.reporting_staff_ids],
        "status": view.status or view.incident.status,
    }


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
    selection = _normalize_selection(reporting_staff_ids)
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
    selection = _active_selection(session, selection)

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
    view = IncidentView(
        incident, selection, revision_number=1, status=incident.status,
        content=content, updated_at=fixed,
    )
    complete_idempotency(
        session, claim, response_status=201,
        response_reference=_response_reference(view), now=fixed,
    )
    session.flush()
    return view


def save_incident_record(
    session: Session, actor: Actor, incident_id: UUID,
    request_model: SaveIncidentRequest, idempotency_key: str, *,
    now: datetime | None = None, request_id: str, client_version: str,
    audit_writer: AuditWriter | None = None,
) -> IncidentView:
    validated = SaveIncidentRequest.model_validate(request_model)
    fixed = now or datetime.now(UTC)
    canonical = {"incident_id": str(incident_id), **validated.model_dump(mode="json")}
    claim = claim_idempotency(
        session, actor, key=idempotency_key, action="incident.save",
        request_sha256=request_digest(canonical), now=fixed,
    )
    if claim.replayed:
        return _view_from_reference(session, actor, claim.response_reference or {})
    current = get_incident(session, actor, incident_id)
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
    view = IncidentView(
        incident, current.reporting_staff_ids, revision_number=next_number,
        status=incident.status, content=payload, updated_at=fixed,
    )
    complete_idempotency(
        session, claim, response_status=200,
        response_reference=_response_reference(view), now=fixed,
    )
    session.flush()
    return view


def list_incident_revisions(
    session: Session, actor: Actor, incident_id: UUID, *, limit: int = 100,
    cursor: dict[str, str] | None = None,
) -> IncidentRevisionPage:
    get_incident(session, actor, incident_id)
    statement = select(IncidentRevision).where(IncidentRevision.incident_id == incident_id)
    if cursor:
        cursor_id = UUID(cursor["id"])
        cursor_row = session.scalar(select(IncidentRevision).where(
            IncidentRevision.incident_id == incident_id,
            IncidentRevision.id == cursor_id,
        ))
        if cursor_row is None or cursor_row.created_at.isoformat() != cursor["created_at"]:
            raise ValueError("revision cursor is invalid")
        statement = statement.where(or_(
            IncidentRevision.revision_number > cursor_row.revision_number,
            and_(
                IncidentRevision.revision_number == cursor_row.revision_number,
                IncidentRevision.id > cursor_row.id,
            ),
        ))
    rows = list(session.scalars(statement.order_by(
        IncidentRevision.revision_number, IncidentRevision.id,
    ).limit(limit + 1)).all())
    page_rows = rows[:limit]
    next_cursor = None
    if len(rows) > limit:
        last = page_rows[-1]
        next_cursor = {"created_at": last.created_at.isoformat(), "id": str(last.id)}
    return IncidentRevisionPage(page_rows, next_cursor)


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
    fixed = now or datetime.now(UTC)
    canonical = {"incident_id": str(incident_id), "revision_number": revision_number}
    claim = claim_idempotency(
        session, actor, key=idempotency_key, action="incident.restore",
        request_sha256=request_digest(canonical), now=fixed,
    )
    if claim.replayed:
        return _view_from_reference(session, actor, claim.response_reference or {})
    current = get_incident(session, actor, incident_id)
    incident = session.scalar(select(Incident).where(
        Incident.id == incident_id).with_for_update())
    if incident is None:
        raise IncidentNotFound("Incident not found.")
    source = get_incident_revision(session, actor, incident_id, revision_number)
    validated = IncidentSnapshotV1.model_validate_json(json.dumps(
        _content_from_snapshot(source.snapshot)))
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
    view = IncidentView(
        incident, current.reporting_staff_ids, revision_number=next_number,
        status=incident.status, content=payload, updated_at=fixed,
    )
    complete_idempotency(
        session, claim, response_status=200,
        response_reference=_response_reference(view), now=fixed,
    )
    session.flush()
    return view


def incident_revision_content(revision: IncidentRevision) -> dict:
    return _content_from_snapshot(revision.snapshot)


__all__ = [
    "IncidentNotFound", "IncidentRevisionNotFound", "IncidentRevisionPage", "IncidentView",
    "create_incident", "get_incident", "get_incident_revision",
    "incident_revision_content", "list_incident_revisions",
    "restore_incident_record", "save_incident_record",
]
