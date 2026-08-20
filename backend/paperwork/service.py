"""Revisioned, idempotent operational-paperwork persistence services."""
from datetime import UTC, date, datetime
import json
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from backend.identity.audit import AuditEventInput, AuditWriter, PostgresAuditWriter
from backend.identity.idempotency import (
    claim_idempotency,
    complete_idempotency,
    request_digest,
)
from backend.paperwork.models import (
    PaperworkKind,
    PaperworkPage,
    PaperworkRevisionPage,
    PaperworkView,
)
from backend.paperwork.policy import can_edit_paperwork, can_read_paperwork
from backend.paperwork.schemas import (
    PaperworkSnapshotV1,
    SavePaperworkRequest,
    changed_field_paths,
    snapshot_for_request,
    validate_payload_for_kind,
)
from backend.persistence.models.paperwork import PaperworkRecord, PaperworkRevision


class PaperworkNotFound(LookupError):
    """The record is absent or concealed by current authorization."""


class PaperworkRevisionNotFound(LookupError):
    """The requested immutable revision does not exist."""


class PaperworkRevisionConflict(ValueError):
    """A save used a stale base revision."""

    def __init__(self, current_revision_number: int):
        self.current_revision_number = current_revision_number
        super().__init__("The paperwork changed; reload before saving.")


class PaperworkAlreadyExists(ValueError):
    """A date/shift record already exists and should be reopened."""

    def __init__(self, record_id: UUID):
        self.record_id = record_id
        super().__init__("Paperwork already exists for this date and shift.")


def _kind(value: PaperworkKind | str) -> PaperworkKind:
    try:
        return value if isinstance(value, PaperworkKind) else PaperworkKind(value)
    except ValueError:
        raise ValueError("paperwork kind is invalid") from None


def _view(record: PaperworkRecord) -> PaperworkView:
    return PaperworkView(
        record_id=record.id,
        kind=PaperworkKind(record.kind),
        work_date=record.work_date,
        shift=record.shift,
        current_revision_number=record.current_revision_number,
        payload=dict(record.current_payload or {}),
        created_by_staff_member_id=record.created_by_staff_member_id,
        last_editor_staff_member_id=record.last_editor_staff_member_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _record_snapshot(record: PaperworkRecord) -> dict[str, object]:
    return PaperworkSnapshotV1(
        kind=record.kind,
        work_date=record.work_date,
        shift=record.shift,
        payload=dict(record.current_payload or {}),
    ).model_dump(mode="json")


def _locked_record(
    session: Session,
    actor,
    record_id: UUID,
) -> PaperworkRecord:
    record = session.scalar(
        select(PaperworkRecord)
        .where(PaperworkRecord.id == record_id)
        .with_for_update()
    )
    if record is None or not can_edit_paperwork(actor, record):
        raise PaperworkNotFound("Paperwork record not found.")
    return record


def get_paperwork_record(
    session: Session,
    actor,
    record_id: UUID,
) -> PaperworkView:
    record = session.get(PaperworkRecord, record_id)
    if record is None or not can_read_paperwork(actor, record):
        raise PaperworkNotFound("Paperwork record not found.")
    return _view(record)


def _view_from_reference(
    session: Session,
    actor,
    reference: dict[str, object],
) -> PaperworkView:
    try:
        record_id = UUID(str(reference["record_id"]))
        revision_number = int(reference["revision_number"])
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("paperwork idempotency reference is invalid") from None
    view = get_paperwork_record(session, actor, record_id)
    if revision_number < 1 or view.current_revision_number < revision_number:
        raise RuntimeError("paperwork idempotency reference is invalid")
    return view


def _audit(
    session: Session,
    actor,
    *,
    action: str,
    record: PaperworkRecord,
    request_id: str,
    client_version: str,
    details: dict[str, object],
    audit_writer: AuditWriter | None,
) -> None:
    (audit_writer or PostgresAuditWriter()).append(
        session,
        AuditEventInput(
            actor_account_id=actor.account_id,
            actor_staff_member_id=actor.staff_member_id,
            action=action,
            result="success",
            request_id=request_id,
            target_type="paperwork_record",
            target_id=record.id,
            details=details,
            client_version=client_version,
        ),
    )


def save_paperwork_record(
    session: Session,
    actor,
    *,
    kind: PaperworkKind | str,
    request_model: SavePaperworkRequest,
    idempotency_key: str,
    request_id: str,
    client_version: str,
    record_id: UUID | None = None,
    now: datetime | None = None,
    audit_writer: AuditWriter | None = None,
) -> PaperworkView:
    """Create or append one immutable paperwork revision in the caller transaction."""
    selected_kind = _kind(kind)
    validated = SavePaperworkRequest.model_validate(request_model)
    validated = validated.model_copy(update={
        "payload": validate_payload_for_kind(selected_kind, validated.payload),
    })
    snapshot = snapshot_for_request(selected_kind, validated)
    fixed = now or datetime.now(UTC)
    action = "paperwork.create" if record_id is None else "paperwork.save"
    canonical = {
        "record_id": str(record_id) if record_id else None,
        "kind": selected_kind.value,
        "request": validated.model_dump(mode="json"),
    }

    record: PaperworkRecord | None = None
    previous_snapshot: dict[str, object] | None = None
    if record_id is None:
        if validated.base_revision_number is not None:
            raise ValueError("New paperwork must not include a base revision.")
    else:
        if validated.base_revision_number is None:
            raise ValueError("Existing paperwork requires a base revision.")
        record = _locked_record(session, actor, record_id)
        if record.kind != selected_kind.value:
            raise ValueError("paperwork kind does not match the record")
        if record.current_revision_number != validated.base_revision_number:
            raise PaperworkRevisionConflict(record.current_revision_number)
        previous_snapshot = _record_snapshot(record)

    claim = claim_idempotency(
        session,
        actor,
        key=idempotency_key,
        action=action,
        request_sha256=request_digest(canonical),
        now=fixed,
    )
    if claim.replayed:
        return _view_from_reference(session, actor, claim.response_reference or {})

    if record is None:
        record = PaperworkRecord(
            id=uuid4(),
            kind=selected_kind.value,
            work_date=validated.work_date,
            shift=validated.shift,
            current_revision_number=1,
            current_payload=dict(validated.payload),
            created_by_account_id=actor.account_id,
            created_by_staff_member_id=actor.staff_member_id,
            last_editor_account_id=actor.account_id,
            last_editor_staff_member_id=actor.staff_member_id,
            created_at=fixed,
            updated_at=fixed,
        )
        session.add(record)
        revision_number = 1
        audit_action = "paperwork.created"
    else:
        revision_number = record.current_revision_number + 1
        record.work_date = validated.work_date
        record.shift = validated.shift
        record.current_revision_number = revision_number
        record.current_payload = dict(validated.payload)
        record.last_editor_account_id = actor.account_id
        record.last_editor_staff_member_id = actor.staff_member_id
        record.updated_at = fixed
        audit_action = "paperwork.saved"

    paths = changed_field_paths(previous_snapshot, snapshot)
    session.add(PaperworkRevision(
        id=uuid4(),
        record_id=record.id,
        revision_number=revision_number,
        editor_account_id=actor.account_id,
        editor_staff_member_id=actor.staff_member_id,
        snapshot=snapshot,
        changed_fields={"paths": list(paths)},
        reason=validated.reason,
        client_version=client_version,
        request_id=request_id,
        created_at=fixed,
    ))
    if audit_action == "paperwork.created":
        details = {
            "record_id": str(record.id),
            "kind": selected_kind.value,
            "revision_number": revision_number,
        }
        response_status = 201
    else:
        details = {
            "record_id": str(record.id),
            "kind": selected_kind.value,
            "revision_number": revision_number,
            "changed_fields": list(paths),
            "reason": validated.reason,
        }
        response_status = 200
    _audit(
        session,
        actor,
        action=audit_action,
        record=record,
        request_id=request_id,
        client_version=client_version,
        details=details,
        audit_writer=audit_writer,
    )
    complete_idempotency(
        session,
        claim,
        response_status=response_status,
        response_reference={
            "record_id": str(record.id),
            "revision_number": revision_number,
        },
        now=fixed,
    )
    session.flush()
    return _view(record)


def copy_previous_daily_record(
    session: Session,
    actor,
    *,
    kind: PaperworkKind | str,
    target_work_date: date,
    shift: str,
    idempotency_key: str,
    request_id: str,
    client_version: str,
    source_record_id: UUID | None = None,
    now: datetime | None = None,
    audit_writer: AuditWriter | None = None,
) -> PaperworkView:
    """Create a reset roster from the latest earlier record for the shift."""
    from backend.paperwork.daily import prepare_copied_roster_payload

    selected_kind = _kind(kind)
    if selected_kind is not PaperworkKind.ASSIGNMENT_ROSTER:
        raise ValueError("copy previous is supported only for assignment rosters")
    if actor.role != "admin":
        raise PaperworkNotFound("Paperwork record not found.")

    normalized_shift = " ".join(shift.split())
    if not normalized_shift or len(normalized_shift) > 32:
        raise ValueError("shift is invalid")

    existing = session.scalar(select(PaperworkRecord).where(
        PaperworkRecord.kind == selected_kind.value,
        PaperworkRecord.work_date == target_work_date,
        PaperworkRecord.shift == normalized_shift,
    ))
    if existing is not None:
        raise PaperworkAlreadyExists(existing.id)

    source_statement = select(PaperworkRecord).where(
        PaperworkRecord.kind == selected_kind.value,
        PaperworkRecord.work_date < target_work_date,
        PaperworkRecord.shift == normalized_shift,
    )
    if source_record_id is not None:
        source_statement = source_statement.where(PaperworkRecord.id == source_record_id)
    source = session.scalar(source_statement.order_by(
        PaperworkRecord.work_date.desc(),
        PaperworkRecord.updated_at.desc(),
        PaperworkRecord.id.desc(),
    ))
    if source is None:
        raise PaperworkNotFound("No earlier assignment roster was found.")

    copied = prepare_copied_roster_payload(
        dict(source.current_payload or {}),
        target_work_date=target_work_date,
        shift=normalized_shift,
    )
    request_model = SavePaperworkRequest(
        schema_version=1,
        work_date=target_work_date,
        shift=normalized_shift,
        payload=copied.model_dump(mode="json"),
        base_revision_number=None,
        reason="manual_save",
    )
    return save_paperwork_record(
        session,
        actor,
        kind=selected_kind,
        request_model=request_model,
        idempotency_key=idempotency_key,
        request_id=request_id,
        client_version=client_version,
        record_id=None,
        now=now,
        audit_writer=audit_writer,
    )


def list_paperwork_records(
    session: Session,
    actor,
    *,
    kind: PaperworkKind | str | None = None,
    limit: int = 25,
    cursor: dict[str, str] | None = None,
) -> PaperworkPage:
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 50:
        raise ValueError("paperwork page size is invalid")
    statement = select(PaperworkRecord)
    if actor.role != "admin":
        statement = statement.where(
            PaperworkRecord.created_by_staff_member_id == actor.staff_member_id
        )
    if kind is not None:
        statement = statement.where(PaperworkRecord.kind == _kind(kind).value)
    if cursor:
        try:
            cursor_time = datetime.fromisoformat(
                cursor["updated_at"].replace("Z", "+00:00")
            )
            cursor_id = UUID(cursor["id"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("paperwork cursor is invalid") from None
        statement = statement.where(or_(
            PaperworkRecord.updated_at < cursor_time,
            and_(
                PaperworkRecord.updated_at == cursor_time,
                PaperworkRecord.id < cursor_id,
            ),
        ))
    rows = list(session.scalars(
        statement.order_by(
            PaperworkRecord.updated_at.desc(),
            PaperworkRecord.id.desc(),
        ).limit(limit + 1)
    ).all())
    page_rows = rows[:limit]
    next_cursor = None
    if len(rows) > limit and page_rows:
        last = page_rows[-1]
        next_cursor = {
            "updated_at": last.updated_at.isoformat(),
            "id": str(last.id),
        }
    return PaperworkPage(tuple(_view(row) for row in page_rows), next_cursor)


def list_paperwork_revisions(
    session: Session,
    actor,
    record_id: UUID,
    *,
    limit: int = 25,
    cursor: dict[str, str] | None = None,
) -> PaperworkRevisionPage:
    get_paperwork_record(session, actor, record_id)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("paperwork revision page size is invalid")
    statement = select(PaperworkRevision).where(
        PaperworkRevision.record_id == record_id
    )
    if cursor:
        try:
            revision_number = int(cursor["revision_number"])
            cursor_id = UUID(cursor["id"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("paperwork revision cursor is invalid") from None
        statement = statement.where(or_(
            PaperworkRevision.revision_number > revision_number,
            and_(
                PaperworkRevision.revision_number == revision_number,
                PaperworkRevision.id > cursor_id,
            ),
        ))
    rows = list(session.scalars(
        statement.order_by(
            PaperworkRevision.revision_number,
            PaperworkRevision.id,
        ).limit(limit + 1)
    ).all())
    page_rows = rows[:limit]
    next_cursor = None
    if len(rows) > limit and page_rows:
        last = page_rows[-1]
        next_cursor = {
            "revision_number": str(last.revision_number),
            "id": str(last.id),
        }
    return PaperworkRevisionPage(tuple(page_rows), next_cursor)


def get_paperwork_revision(
    session: Session,
    actor,
    record_id: UUID,
    revision_number: int,
) -> PaperworkRevision:
    get_paperwork_record(session, actor, record_id)
    revision = session.scalar(select(PaperworkRevision).where(
        PaperworkRevision.record_id == record_id,
        PaperworkRevision.revision_number == revision_number,
    ))
    if revision is None:
        raise PaperworkRevisionNotFound("Paperwork revision not found.")
    return revision


def restore_paperwork_record(
    session: Session,
    actor,
    *,
    record_id: UUID,
    source_revision_number: int,
    idempotency_key: str,
    request_id: str,
    client_version: str,
    now: datetime | None = None,
    audit_writer: AuditWriter | None = None,
) -> PaperworkView:
    if (
        not isinstance(source_revision_number, int)
        or isinstance(source_revision_number, bool)
        or source_revision_number < 1
    ):
        raise ValueError("source revision is invalid")
    fixed = now or datetime.now(UTC)
    record = _locked_record(session, actor, record_id)
    source = session.scalar(select(PaperworkRevision).where(
        PaperworkRevision.record_id == record_id,
        PaperworkRevision.revision_number == source_revision_number,
    ))
    if source is None:
        raise PaperworkRevisionNotFound("Paperwork revision not found.")
    canonical = {
        "record_id": str(record_id),
        "source_revision_number": source_revision_number,
    }
    claim = claim_idempotency(
        session,
        actor,
        key=idempotency_key,
        action="paperwork.restore",
        request_sha256=request_digest(canonical),
        now=fixed,
    )
    if claim.replayed:
        return _view_from_reference(session, actor, claim.response_reference or {})

    source_snapshot_model = PaperworkSnapshotV1.model_validate_json(
        json.dumps(source.snapshot, ensure_ascii=False, allow_nan=False)
    )
    source_snapshot = source_snapshot_model.model_dump(mode="json")
    previous_snapshot = _record_snapshot(record)
    revision_number = record.current_revision_number + 1
    paths = changed_field_paths(previous_snapshot, source_snapshot)

    record.kind = source_snapshot_model.kind
    record.work_date = source_snapshot_model.work_date
    record.shift = source_snapshot_model.shift
    record.current_revision_number = revision_number
    record.current_payload = dict(source_snapshot_model.payload)
    record.last_editor_account_id = actor.account_id
    record.last_editor_staff_member_id = actor.staff_member_id
    record.updated_at = fixed
    session.add(PaperworkRevision(
        id=uuid4(),
        record_id=record.id,
        revision_number=revision_number,
        editor_account_id=actor.account_id,
        editor_staff_member_id=actor.staff_member_id,
        snapshot=source_snapshot,
        changed_fields={"paths": list(paths)},
        reason="restored",
        client_version=client_version,
        request_id=request_id,
        created_at=fixed,
    ))
    _audit(
        session,
        actor,
        action="paperwork.restored",
        record=record,
        request_id=request_id,
        client_version=client_version,
        details={
            "record_id": str(record.id),
            "kind": record.kind,
            "revision_number": revision_number,
            "source_revision_number": source_revision_number,
        },
        audit_writer=audit_writer,
    )
    complete_idempotency(
        session,
        claim,
        response_status=200,
        response_reference={
            "record_id": str(record.id),
            "revision_number": revision_number,
        },
        now=fixed,
    )
    session.flush()
    return _view(record)
