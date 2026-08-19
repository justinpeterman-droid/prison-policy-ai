"""Authorized, caller-transaction-owned incident persistence operations."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, date, datetime
import json
from uuid import UUID, uuid4

from sqlalchemy import and_, event, or_, select
from sqlalchemy.orm import Session, aliased

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
    ReportRevision,
)
from backend.reports.revisions import (
    RevisionConflict,
    RevisionTargetMissing,
    create_recovery_revision,
    restore_report,
    save_report,
    save_report_status,
    transfer_report_ownership,
)
from backend.webapp.api_v1.middleware import Actor
from backend.webapp.api_v1.schemas.reporting import (
    IncidentSnapshotV1,
    ReportContentV1,
    SaveIncidentRequest,
    SaveReportRequest,
    changed_field_names,
)


SERVER_METADATA_KEY = "server_metadata"
REPORTING_STAFF_IDS_KEY = "reporting_staff_ids"
MAX_REPORTING_STAFF = 20


class IncidentNotFound(LookupError):
    pass


class IncidentRevisionNotFound(LookupError):
    pass


class ReportNotFound(LookupError):
    pass


class ReportRevisionNotFound(LookupError):
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


@dataclass(frozen=True)
class ReportView:
    report: Report
    content: dict
    revision_number: int
    status: str
    updated_at: datetime
    editor_staff_member_id: UUID
    editor_display_name: str
    reporting_staff_member_id: UUID | None = None
    reporting_officer_display_name: str | None = None
    prepared_by_staff_member_id: UUID | None = None
    preparer_display_name: str | None = None


@dataclass(frozen=True)
class ReportSummaryRow:
    report: Report
    incident: Incident
    reporting_officer_display_name: str
    preparer_display_name: str
    relationship: str


@dataclass(frozen=True)
class ReportPage:
    items: list[ReportSummaryRow]
    next_cursor: dict[str, str] | None


@dataclass(frozen=True)
class ReportRevisionPage:
    items: list[ReportRevision]
    next_cursor: dict[str, str] | None


@dataclass(frozen=True)
class AdminReportFilters:
    """One closed set of bounded, indexed, structured-column search filters.

    Reused as-is by RP-09 bulk export. Every field is optional; the caller
    (route layer) is responsible for rejecting unknown or empty-string query
    fields before constructing this.
    """

    report_id: UUID | None = None
    incident_id: UUID | None = None
    reporting_staff_id: UUID | None = None
    preparer_staff_id: UUID | None = None
    incident_date_from: date | None = None
    incident_date_to: date | None = None
    created_at_from: datetime | None = None
    created_at_to: datetime | None = None
    inmate_first_name: str | None = None
    inmate_middle_name: str | None = None
    inmate_last_name: str | None = None
    inmate_adc_number: str | None = None
    category: str | None = None
    facility: str | None = None
    location: str | None = None
    shift: str | None = None
    status: str | None = None
    last_editor_staff_id: UUID | None = None
    modified_at_from: datetime | None = None
    modified_at_to: datetime | None = None


ADMIN_REPORT_FILTER_FIELDS: tuple[str, ...] = tuple(AdminReportFilters.__dataclass_fields__)
ADMIN_REPORT_SEARCH_SORTS: dict[str, bool] = {
    "updated_at_desc": True,
    "updated_at_asc": False,
    "created_at_desc": True,
    "created_at_asc": False,
}
ADMIN_REPORT_SEARCH_MAX_PAGE_SIZE = 100
ADMIN_REPORT_SEARCH_DEFAULT_PAGE_SIZE = 50


@dataclass(frozen=True)
class AdminReportSearchItem:
    report: Report
    incident: Incident
    last_editor_staff_member_id: UUID
    inmate_adc_numbers: tuple[str, ...]


@dataclass(frozen=True)
class AdminReportSearchPage:
    items: list[AdminReportSearchItem]
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
        "incident_number", "incident_name", "incident_date", "incident_time",
        "facility", "shift", "location", "category",
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
        changed_fields={"fields": [
            field for field in ("incident_number", "incident_name", "field_notes")
            if content.get(field)
        ]},
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
            "incident_number", "incident_name", "incident_date", "incident_time",
            "facility", "shift", "location", "category",
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
            "incident_number", "incident_name", "incident_date", "incident_time",
            "facility", "shift", "location", "category",
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


def _display_name(staff: StaffMember) -> str:
    return " ".join(
        part for part in (staff.rank, staff.first_name, staff.last_name) if part
    )


def _authorized_report_statement(actor: Actor, report_id: UUID | None = None):
    statement = select(Report).join(
        ReportAccess, ReportAccess.report_id == Report.id,
    ).where(
        ReportAccess.staff_member_id == actor.staff_member_id,
        ReportAccess.revoked_at.is_(None),
    )
    if report_id is not None:
        statement = statement.where(Report.id == report_id)
    return statement


def _lock_authorized_report(
    session: Session, actor: Actor, report_id: UUID,
) -> Report:
    """Lock the report, then its live employee access, in one transaction."""
    report = session.scalar(
        select(Report).where(Report.id == report_id).with_for_update()
    )
    if report is None:
        raise ReportNotFound("Report not found.")
    access = session.scalar(select(ReportAccess).where(
        ReportAccess.report_id == report_id,
        ReportAccess.staff_member_id == actor.staff_member_id,
        ReportAccess.revoked_at.is_(None),
    ).with_for_update())
    if access is None:
        raise ReportNotFound("Report not found.")
    return report


def _report_revision_view(
    session: Session, report: Report, revision: ReportRevision, *,
    status: str | None = None, current_revision_number: int | None = None,
) -> ReportView:
    editor = session.get(StaffMember, revision.editor_staff_member_id)
    if editor is None:
        raise RuntimeError("report revision editor is unavailable")
    return ReportView(
        report=report,
        content=ReportContentV1.model_validate(revision.snapshot).model_dump(mode="json"),
        revision_number=(
            revision.revision_number
            if current_revision_number is None else current_revision_number
        ),
        status=status or report.status,
        updated_at=revision.created_at,
        editor_staff_member_id=revision.editor_staff_member_id,
        editor_display_name=_display_name(editor),
    )


def get_report(session: Session, actor: Actor, report_id: UUID) -> ReportView:
    """Load a report only through its live owner/preparer relationship."""
    report = session.scalar(_authorized_report_statement(actor, report_id))
    if report is None:
        raise ReportNotFound("Report not found.")
    revision = session.scalar(select(ReportRevision).where(
        ReportRevision.report_id == report.id,
        ReportRevision.revision_number == report.current_revision_number,
    ))
    if revision is None:
        raise ReportNotFound("Report not found.")
    return _report_revision_view(session, report, revision)


def list_reports(
    session: Session,
    actor: Actor,
    *,
    relationship: str,
    limit: int = 25,
    cursor: dict[str, str] | None = None,
    status: str | None = None,
    incident_date_from=None,
    incident_date_to=None,
    category: str | None = None,
    updated_at_from: datetime | None = None,
    updated_at_to: datetime | None = None,
) -> ReportPage:
    """Return an authorization-scoped keyset page with no report content."""
    if relationship not in {"owned", "prepared"}:
        raise ValueError("relationship is invalid")
    owner = aliased(StaffMember)
    preparer = aliased(StaffMember)
    relationship_name = "owner" if relationship == "owned" else "preparer"
    statement = (
        select(Report, Incident, owner, preparer)
        .join(ReportAccess, ReportAccess.report_id == Report.id)
        .join(Incident, Incident.id == Report.incident_id)
        .join(owner, owner.id == Report.reporting_staff_member_id)
        .join(preparer, preparer.id == Report.prepared_by_staff_member_id)
        .where(
            ReportAccess.staff_member_id == actor.staff_member_id,
            ReportAccess.relationship == relationship_name,
            ReportAccess.revoked_at.is_(None),
        )
    )
    if status is not None:
        statement = statement.where(Report.status == status)
    if incident_date_from is not None:
        statement = statement.where(Incident.incident_date >= incident_date_from)
    if incident_date_to is not None:
        statement = statement.where(Incident.incident_date <= incident_date_to)
    if category is not None:
        statement = statement.where(Incident.category == category)
    if updated_at_from is not None:
        statement = statement.where(Report.updated_at >= updated_at_from)
    if updated_at_to is not None:
        statement = statement.where(Report.updated_at <= updated_at_to)
    if cursor:
        cursor_time = datetime.fromisoformat(cursor["created_at"].replace("Z", "+00:00"))
        cursor_id = UUID(cursor["id"])
        statement = statement.where(or_(
            Report.updated_at < cursor_time,
            and_(Report.updated_at == cursor_time, Report.id < cursor_id),
        ))
    rows = session.execute(statement.order_by(
        Report.updated_at.desc(), Report.id.desc(),
    ).limit(limit + 1)).all()
    page_rows = rows[:limit]
    items = [
        ReportSummaryRow(
            report=row[0], incident=row[1],
            reporting_officer_display_name=_display_name(row[2]),
            preparer_display_name=_display_name(row[3]),
            relationship=relationship,
        )
        for row in page_rows
    ]
    next_cursor = None
    if len(rows) > limit:
        last = page_rows[-1][0]
        next_cursor = {"created_at": last.updated_at.isoformat(), "id": str(last.id)}
    return ReportPage(items, next_cursor)


def list_report_revisions(
    session: Session, actor: Actor, report_id: UUID, *, limit: int = 25,
    cursor: dict[str, str] | None = None,
) -> ReportRevisionPage:
    get_report(session, actor, report_id)
    statement = select(ReportRevision).where(ReportRevision.report_id == report_id)
    if cursor:
        cursor_id = UUID(cursor["id"])
        cursor_row = session.scalar(select(ReportRevision).where(
            ReportRevision.report_id == report_id,
            ReportRevision.id == cursor_id,
        ))
        if cursor_row is None or cursor_row.created_at.isoformat() != cursor["created_at"]:
            raise ValueError("revision cursor is invalid")
        statement = statement.where(or_(
            ReportRevision.revision_number > cursor_row.revision_number,
            and_(
                ReportRevision.revision_number == cursor_row.revision_number,
                ReportRevision.id > cursor_row.id,
            ),
        ))
    rows = list(session.scalars(statement.order_by(
        ReportRevision.revision_number, ReportRevision.id,
    ).limit(limit + 1)).all())
    page_rows = rows[:limit]
    next_cursor = None
    if len(rows) > limit:
        last = page_rows[-1]
        next_cursor = {"created_at": last.created_at.isoformat(), "id": str(last.id)}
    return ReportRevisionPage(page_rows, next_cursor)


def get_report_revision(
    session: Session, actor: Actor, report_id: UUID, revision_number: int,
) -> ReportRevision:
    get_report(session, actor, report_id)
    revision = session.scalar(select(ReportRevision).where(
        ReportRevision.report_id == report_id,
        ReportRevision.revision_number == revision_number,
    ))
    if revision is None:
        raise ReportRevisionNotFound("Report revision not found.")
    return revision


def report_revision_content(revision: ReportRevision) -> dict:
    return ReportContentV1.model_validate(revision.snapshot).model_dump(mode="json")


def get_report_admin(session: Session, report_id: UUID) -> ReportView:
    """Load any report for an already-authorized Admin actor.

    Existence, not a client-owned relationship, is the only precondition;
    Admin authorization (role plus active elevation) is enforced by the
    route-level guard before this is ever called.
    """
    report = session.get(Report, report_id)
    if report is None:
        raise ReportNotFound("Report not found.")
    revision = session.scalar(select(ReportRevision).where(
        ReportRevision.report_id == report.id,
        ReportRevision.revision_number == report.current_revision_number,
    ))
    if revision is None:
        raise ReportNotFound("Report not found.")
    return _report_revision_view(session, report, revision)


def list_report_revisions_admin(
    session: Session, report_id: UUID, *, limit: int = 25,
    cursor: dict[str, str] | None = None,
) -> ReportRevisionPage:
    if session.get(Report, report_id) is None:
        raise ReportNotFound("Report not found.")
    statement = select(ReportRevision).where(ReportRevision.report_id == report_id)
    if cursor:
        cursor_id = UUID(cursor["id"])
        cursor_row = session.scalar(select(ReportRevision).where(
            ReportRevision.report_id == report_id,
            ReportRevision.id == cursor_id,
        ))
        if cursor_row is None or cursor_row.created_at.isoformat() != cursor["created_at"]:
            raise ValueError("revision cursor is invalid")
        statement = statement.where(or_(
            ReportRevision.revision_number > cursor_row.revision_number,
            and_(
                ReportRevision.revision_number == cursor_row.revision_number,
                ReportRevision.id > cursor_row.id,
            ),
        ))
    rows = list(session.scalars(statement.order_by(
        ReportRevision.revision_number, ReportRevision.id,
    ).limit(limit + 1)).all())
    page_rows = rows[:limit]
    next_cursor = None
    if len(rows) > limit:
        last = page_rows[-1]
        next_cursor = {"created_at": last.created_at.isoformat(), "id": str(last.id)}
    return ReportRevisionPage(page_rows, next_cursor)


def get_report_revision_admin(
    session: Session, report_id: UUID, revision_number: int,
) -> ReportRevision:
    if session.get(Report, report_id) is None:
        raise ReportNotFound("Report not found.")
    revision = session.scalar(select(ReportRevision).where(
        ReportRevision.report_id == report_id,
        ReportRevision.revision_number == revision_number,
    ))
    if revision is None:
        raise ReportRevisionNotFound("Report revision not found.")
    return revision


def _inmate_adc_numbers(extracted_facts: object) -> tuple[str, ...]:
    persons = extracted_facts.get("persons") if isinstance(extracted_facts, dict) else None
    if not isinstance(persons, list):
        return ()
    numbers: list[str] = []
    for person in persons:
        if not isinstance(person, dict) or person.get("role") != "inmate":
            continue
        adc = person.get("adc_number")
        if isinstance(adc, str) and adc and adc not in numbers:
            numbers.append(adc)
    return tuple(numbers)


_ADMIN_INMATE_FILTER_COLUMNS = {
    "inmate_first_name": "first",
    "inmate_middle_name": "middle",
    "inmate_last_name": "last",
}


def admin_search_reports(
    session: Session, filters: AdminReportFilters, *,
    limit: int = ADMIN_REPORT_SEARCH_DEFAULT_PAGE_SIZE,
    cursor: dict[str, str] | None = None, sort: str = "updated_at_desc",
    actor: Actor, request_id: str, client_version: str,
    audit_writer: AuditWriter | None = None,
) -> AdminReportSearchPage:
    """Bounded, indexed, structured-column Admin search.

    Every predicate reads a structured column (report/incident fields or
    structured `extracted_facts` persons entries) -- never the free-text
    narrative or field notes. Writes exactly one bounded audit event naming
    the filters that were used (never their values) and the result count.
    """
    if sort not in ADMIN_REPORT_SEARCH_SORTS:
        raise ValueError("sort is invalid")
    descending = ADMIN_REPORT_SEARCH_SORTS[sort]
    sort_column = Report.updated_at if sort.startswith("updated_at") else Report.created_at

    current_revision = aliased(ReportRevision)
    statement = (
        select(Report, Incident, current_revision)
        .join(Incident, Incident.id == Report.incident_id)
        .join(current_revision, and_(
            current_revision.report_id == Report.id,
            current_revision.revision_number == Report.current_revision_number,
        ))
    )
    if filters.report_id is not None:
        statement = statement.where(Report.id == filters.report_id)
    if filters.incident_id is not None:
        statement = statement.where(Report.incident_id == filters.incident_id)
    if filters.reporting_staff_id is not None:
        statement = statement.where(
            Report.reporting_staff_member_id == filters.reporting_staff_id)
    if filters.preparer_staff_id is not None:
        statement = statement.where(
            Report.prepared_by_staff_member_id == filters.preparer_staff_id)
    if filters.incident_date_from is not None:
        statement = statement.where(Incident.incident_date >= filters.incident_date_from)
    if filters.incident_date_to is not None:
        statement = statement.where(Incident.incident_date <= filters.incident_date_to)
    if filters.created_at_from is not None:
        statement = statement.where(Report.created_at >= filters.created_at_from)
    if filters.created_at_to is not None:
        statement = statement.where(Report.created_at <= filters.created_at_to)
    if filters.category is not None:
        statement = statement.where(Incident.category == filters.category)
    if filters.facility is not None:
        statement = statement.where(Incident.facility == filters.facility)
    if filters.location is not None:
        statement = statement.where(Incident.location == filters.location)
    if filters.shift is not None:
        statement = statement.where(Incident.shift == filters.shift)
    if filters.status is not None:
        statement = statement.where(Report.status == filters.status)
    if filters.last_editor_staff_id is not None:
        statement = statement.where(
            current_revision.editor_staff_member_id == filters.last_editor_staff_id)
    if filters.modified_at_from is not None:
        statement = statement.where(Report.updated_at >= filters.modified_at_from)
    if filters.modified_at_to is not None:
        statement = statement.where(Report.updated_at <= filters.modified_at_to)

    inmate_person: dict[str, str] = {"role": "inmate"}
    for field_name, person_key in _ADMIN_INMATE_FILTER_COLUMNS.items():
        value = getattr(filters, field_name)
        if value is not None:
            inmate_person[person_key] = value
    if filters.inmate_adc_number is not None:
        inmate_person["adc_number"] = filters.inmate_adc_number
    if len(inmate_person) > 1:
        # JSONB containment keeps all requested attributes on the same inmate
        # object and is accelerated by 0004's jsonb_path_ops GIN index.
        statement = statement.where(
            Incident.extracted_facts.contains({"persons": [inmate_person]})
        )

    if cursor:
        cursor_time = datetime.fromisoformat(cursor["created_at"].replace("Z", "+00:00"))
        cursor_id = UUID(cursor["id"])
        if descending:
            statement = statement.where(or_(
                sort_column < cursor_time,
                and_(sort_column == cursor_time, Report.id < cursor_id),
            ))
        else:
            statement = statement.where(or_(
                sort_column > cursor_time,
                and_(sort_column == cursor_time, Report.id > cursor_id),
            ))
    order = (
        (sort_column.desc(), Report.id.desc()) if descending
        else (sort_column.asc(), Report.id.asc())
    )
    rows = session.execute(statement.order_by(*order).limit(limit + 1)).all()
    page_rows = rows[:limit]
    items = [
        AdminReportSearchItem(
            report=row[0], incident=row[1],
            last_editor_staff_member_id=row[2].editor_staff_member_id,
            inmate_adc_numbers=_inmate_adc_numbers(row[1].extracted_facts),
        )
        for row in page_rows
    ]
    next_cursor = None
    if len(rows) > limit:
        last_report = page_rows[-1][0]
        sort_value = last_report.updated_at if sort.startswith("updated_at") else last_report.created_at
        next_cursor = {"created_at": sort_value.isoformat(), "id": str(last_report.id)}

    provided_filters = sorted(
        name for name in ADMIN_REPORT_FILTER_FIELDS if getattr(filters, name) is not None)
    writer = audit_writer or PostgresAuditWriter()
    writer.append(session, AuditEventInput(
        actor_account_id=actor.account_id,
        actor_staff_member_id=actor.staff_member_id,
        action="admin.report_search",
        result="success",
        request_id=request_id,
        target_type="report",
        target_id=None,
        details={"filters": provided_filters, "result_count": len(items)},
        client_version=client_version,
    ))
    session.flush()
    return AdminReportSearchPage(items, next_cursor)


def _report_reference(
    view: ReportView, *, operation_revision_number: int | None = None,
) -> dict[str, object]:
    return {
        "report_id": str(view.report.id),
        "revision_number": operation_revision_number or view.revision_number,
        "current_revision_number": view.revision_number,
        "status": view.status,
    }


def _report_reference_admin(session: Session, view: ReportView) -> dict[str, object]:
    owner = session.get(StaffMember, view.report.reporting_staff_member_id)
    preparer = session.get(StaffMember, view.report.prepared_by_staff_member_id)
    if owner is None or preparer is None:
        raise RuntimeError("report ownership snapshot is unavailable")
    return {
        **_report_reference(view),
        "reporting_staff_member_id": str(owner.id),
        "reporting_officer_display_name": _display_name(owner),
        "prepared_by_staff_member_id": str(preparer.id),
        "preparer_display_name": _display_name(preparer),
        "editor_staff_member_id": str(view.editor_staff_member_id),
        "editor_display_name": view.editor_display_name,
        "updated_at": view.updated_at.isoformat(),
    }


def _report_view_from_reference(
    session: Session, actor: Actor, reference: dict,
) -> tuple[ReportView, int]:
    try:
        report_id = UUID(str(reference["report_id"]))
        revision_number = int(reference["revision_number"])
        current_revision_number = int(reference["current_revision_number"])
        status = str(reference["status"])
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("idempotency reference is invalid") from None
    authorized = get_report(session, actor, report_id)
    revision = session.scalar(select(ReportRevision).where(
        ReportRevision.report_id == report_id,
        ReportRevision.revision_number == revision_number,
    ))
    if revision is None:
        raise RuntimeError("idempotency reference is invalid")
    return (
        _report_revision_view(
            session, authorized.report, revision, status=status,
            current_revision_number=current_revision_number,
        ),
        revision_number,
    )


def _report_view_from_reference_admin(
    session: Session, reference: dict,
) -> ReportView:
    try:
        report_id = UUID(str(reference["report_id"]))
        revision_number = int(reference["revision_number"])
        current_revision_number = int(reference["current_revision_number"])
        status = str(reference["status"])
        reporting_staff_member_id = UUID(str(reference["reporting_staff_member_id"]))
        reporting_officer_display_name = str(reference["reporting_officer_display_name"])
        prepared_by_staff_member_id = UUID(str(reference["prepared_by_staff_member_id"]))
        preparer_display_name = str(reference["preparer_display_name"])
        editor_staff_member_id = UUID(str(reference["editor_staff_member_id"]))
        editor_display_name = str(reference["editor_display_name"])
        updated_at = datetime.fromisoformat(
            str(reference["updated_at"]).replace("Z", "+00:00")
        )
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("idempotency reference is invalid") from None
    if (
        not reporting_officer_display_name.strip()
        or not preparer_display_name.strip()
        or not editor_display_name.strip()
        or updated_at.tzinfo is None
        or updated_at.utcoffset() != UTC.utcoffset(updated_at)
    ):
        raise RuntimeError("idempotency reference is invalid")
    report = session.get(Report, report_id)
    if report is None:
        raise RuntimeError("idempotency reference is invalid")
    revision = session.scalar(select(ReportRevision).where(
        ReportRevision.report_id == report_id,
        ReportRevision.revision_number == revision_number,
    ))
    if revision is None:
        raise RuntimeError("idempotency reference is invalid")
    view = _report_revision_view(
        session, report, revision, status=status,
        current_revision_number=current_revision_number,
    )
    if view.editor_staff_member_id != editor_staff_member_id:
        raise RuntimeError("idempotency reference is invalid")
    return ReportView(
        report=view.report,
        content=view.content,
        revision_number=view.revision_number,
        status=view.status,
        updated_at=updated_at,
        editor_staff_member_id=editor_staff_member_id,
        editor_display_name=editor_display_name,
        reporting_staff_member_id=reporting_staff_member_id,
        reporting_officer_display_name=reporting_officer_display_name,
        prepared_by_staff_member_id=prepared_by_staff_member_id,
        preparer_display_name=preparer_display_name,
    )


def save_report_admin_record(
    session: Session, actor: Actor, report_id: UUID, request_model: SaveReportRequest,
    idempotency_key: str, *, now: datetime | None = None, request_id: str,
    client_version: str, audit_writer: AuditWriter | None = None,
) -> ReportView:
    """Admin edit: same shared revision service, reason fixed to admin_edit."""
    validated = SaveReportRequest.model_validate(request_model)
    fixed = now or datetime.now(UTC)
    canonical = {"report_id": str(report_id), **validated.model_dump(mode="json")}
    claim = claim_idempotency(
        session, actor, key=idempotency_key, action="report.admin_edit",
        request_sha256=request_digest(canonical), now=fixed,
    )
    if claim.replayed:
        return _report_view_from_reference_admin(session, claim.response_reference or {})
    try:
        revision = save_report(
            session, actor, report_id, validated.content,
            validated.base_revision_number, "admin_edit",
            request_id=request_id, client_version=client_version,
            audit_writer=audit_writer,
        )
    except RevisionTargetMissing as error:
        raise ReportNotFound(str(error)) from None
    report = session.get(Report, report_id)
    view = _report_revision_view(session, report, revision)
    complete_idempotency(
        session, claim, response_status=200,
        response_reference=_report_reference_admin(session, view), now=fixed,
    )
    session.flush()
    return view


def restore_report_admin_record(
    session: Session, actor: Actor, report_id: UUID, revision_number: int,
    idempotency_key: str, *, now: datetime | None = None, request_id: str,
    client_version: str, audit_writer: AuditWriter | None = None,
) -> ReportView:
    fixed = now or datetime.now(UTC)
    canonical = {"report_id": str(report_id), "revision_number": revision_number}
    claim = claim_idempotency(
        session, actor, key=idempotency_key, action="report.admin_restore",
        request_sha256=request_digest(canonical), now=fixed,
    )
    if claim.replayed:
        return _report_view_from_reference_admin(session, claim.response_reference or {})
    try:
        revision = restore_report(
            session, actor, report_id, revision_number,
            request_id=request_id, client_version=client_version,
            audit_writer=audit_writer,
        )
    except RevisionTargetMissing as error:
        raise ReportRevisionNotFound(str(error)) from None
    report = session.get(Report, report_id)
    view = _report_revision_view(session, report, revision)
    complete_idempotency(
        session, claim, response_status=200,
        response_reference=_report_reference_admin(session, view), now=fixed,
    )
    session.flush()
    return view


def transfer_report_ownership_record(
    session: Session, actor: Actor, report_id: UUID, new_owner_staff_id: UUID,
    new_preparer_staff_id: UUID | None, reason: str, idempotency_key: str, *,
    now: datetime | None = None, request_id: str, client_version: str,
    audit_writer: AuditWriter | None = None,
) -> ReportView:
    fixed = now or datetime.now(UTC)
    canonical = {
        "report_id": str(report_id),
        "new_owner_staff_id": str(new_owner_staff_id),
        "new_preparer_staff_id": (
            str(new_preparer_staff_id) if new_preparer_staff_id else None),
        "reason": reason,
    }
    claim = claim_idempotency(
        session, actor, key=idempotency_key, action="report.transfer",
        request_sha256=request_digest(canonical), now=fixed,
    )
    if claim.replayed:
        return _report_view_from_reference_admin(session, claim.response_reference or {})
    try:
        revision = transfer_report_ownership(
            session, actor, report_id, new_owner_staff_id, new_preparer_staff_id,
            request_id=request_id, client_version=client_version,
            audit_writer=audit_writer,
        )
    except RevisionTargetMissing as error:
        raise ReportNotFound(str(error)) from None
    report = session.get(Report, report_id)
    view = _report_revision_view(session, report, revision)
    complete_idempotency(
        session, claim, response_status=200,
        response_reference=_report_reference_admin(session, view), now=fixed,
    )
    session.flush()
    return view


def save_report_record(
    session: Session, actor: Actor, report_id: UUID, request_model: SaveReportRequest,
    idempotency_key: str, *, now: datetime | None = None, request_id: str,
    client_version: str, audit_writer: AuditWriter | None = None,
) -> ReportView:
    validated = SaveReportRequest.model_validate(request_model)
    _lock_authorized_report(session, actor, report_id)
    fixed = now or datetime.now(UTC)
    canonical = {"report_id": str(report_id), **validated.model_dump(mode="json")}
    claim = claim_idempotency(
        session, actor, key=idempotency_key, action="report.save",
        request_sha256=request_digest(canonical), now=fixed,
    )
    if claim.replayed:
        return _report_view_from_reference(session, actor, claim.response_reference or {})[0]
    revision = save_report(
        session, actor, report_id, validated.content,
        validated.base_revision_number, validated.reason,
        request_id=request_id, client_version=client_version,
        audit_writer=audit_writer,
    )
    report = session.get(Report, report_id)
    view = _report_revision_view(session, report, revision)
    complete_idempotency(
        session, claim, response_status=200,
        response_reference=_report_reference(view), now=fixed,
    )
    session.flush()
    return view


def save_report_status_record(
    session: Session, actor: Actor, report_id: UUID, status: str,
    base_revision_number: int, idempotency_key: str, *, now: datetime | None = None,
    request_id: str, client_version: str, audit_writer: AuditWriter | None = None,
) -> ReportView:
    _lock_authorized_report(session, actor, report_id)
    fixed = now or datetime.now(UTC)
    canonical = {
        "report_id": str(report_id), "status": status,
        "base_revision_number": base_revision_number,
    }
    claim = claim_idempotency(
        session, actor, key=idempotency_key, action="report.status",
        request_sha256=request_digest(canonical), now=fixed,
    )
    if claim.replayed:
        return _report_view_from_reference(session, actor, claim.response_reference or {})[0]
    revision = save_report_status(
        session, actor, report_id, status, base_revision_number,
        request_id=request_id, client_version=client_version,
        audit_writer=audit_writer,
    )
    report = session.get(Report, report_id)
    view = _report_revision_view(session, report, revision)
    complete_idempotency(
        session, claim, response_status=200,
        response_reference=_report_reference(view), now=fixed,
    )
    session.flush()
    return view


def restore_report_record(
    session: Session, actor: Actor, report_id: UUID, revision_number: int,
    idempotency_key: str, *, now: datetime | None = None, request_id: str,
    client_version: str, audit_writer: AuditWriter | None = None,
) -> ReportView:
    _lock_authorized_report(session, actor, report_id)
    fixed = now or datetime.now(UTC)
    canonical = {"report_id": str(report_id), "revision_number": revision_number}
    claim = claim_idempotency(
        session, actor, key=idempotency_key, action="report.restore",
        request_sha256=request_digest(canonical), now=fixed,
    )
    if claim.replayed:
        return _report_view_from_reference(session, actor, claim.response_reference or {})[0]
    try:
        revision = restore_report(
            session, actor, report_id, revision_number,
            request_id=request_id, client_version=client_version,
            audit_writer=audit_writer,
        )
    except RevisionTargetMissing as error:
        raise ReportRevisionNotFound(str(error)) from None
    report = session.get(Report, report_id)
    view = _report_revision_view(session, report, revision)
    complete_idempotency(
        session, claim, response_status=200,
        response_reference=_report_reference(view), now=fixed,
    )
    session.flush()
    return view


def create_report_recovery_record(
    session: Session, actor: Actor, report_id: UUID, content: ReportContentV1,
    base_revision_number: int, idempotency_key: str, *, now: datetime | None = None,
    request_id: str, client_version: str, audit_writer: AuditWriter | None = None,
) -> tuple[ReportView, int]:
    _lock_authorized_report(session, actor, report_id)
    current = get_report(session, actor, report_id)
    validated = ReportContentV1.model_validate(content)
    fixed = now or datetime.now(UTC)
    canonical = {
        "report_id": str(report_id), "content": validated.model_dump(mode="json"),
        "base_revision_number": base_revision_number,
    }
    claim = claim_idempotency(
        session, actor, key=idempotency_key, action="report.recovery",
        request_sha256=request_digest(canonical), now=fixed,
    )
    if claim.replayed:
        return _report_view_from_reference(session, actor, claim.response_reference or {})
    try:
        recovery = create_recovery_revision(
            session, actor, report_id, validated, base_revision_number,
            request_id=request_id, client_version=client_version,
            audit_writer=audit_writer,
        )
    except RevisionTargetMissing as error:
        raise ReportRevisionNotFound(str(error)) from None
    # The recovery snapshot is returned, while current_revision_number/status
    # remain the cloud state that was deliberately not promoted.
    view = _report_revision_view(
        session, current.report, recovery, status=current.status,
        current_revision_number=current.revision_number,
    )
    complete_idempotency(
        session, claim, response_status=201,
        response_reference=_report_reference(
            view, operation_revision_number=recovery.revision_number),
        now=fixed,
    )
    session.flush()
    return view, recovery.revision_number


__all__ = [
    "AdminReportFilters", "AdminReportSearchItem", "AdminReportSearchPage",
    "ADMIN_REPORT_FILTER_FIELDS", "ADMIN_REPORT_SEARCH_SORTS",
    "ADMIN_REPORT_SEARCH_DEFAULT_PAGE_SIZE", "ADMIN_REPORT_SEARCH_MAX_PAGE_SIZE",
    "IncidentNotFound", "IncidentRevisionNotFound", "IncidentRevisionPage", "IncidentView",
    "ReportNotFound", "ReportPage", "ReportRevisionNotFound", "ReportRevisionPage",
    "ReportSummaryRow", "ReportView", "create_report_recovery_record",
    "create_incident", "get_incident", "get_incident_revision",
    "get_report", "get_report_admin", "get_report_revision", "get_report_revision_admin",
    "list_report_revisions", "list_report_revisions_admin", "list_reports",
    "admin_search_reports",
    "incident_revision_content", "list_incident_revisions",
    "report_revision_content", "restore_report_record", "restore_report_admin_record",
    "save_report_record", "save_report_admin_record", "save_report_status_record",
    "transfer_report_ownership_record",
    "restore_incident_record", "save_incident_record",
]
