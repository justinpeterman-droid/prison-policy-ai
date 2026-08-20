"""Safe, idempotent output-action recording for operational paperwork."""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.identity.audit import AuditEventInput, AuditWriter, PostgresAuditWriter
from backend.identity.idempotency import (
    claim_idempotency,
    complete_idempotency,
    request_digest,
)
from backend.paperwork.models import (
    PaperworkAction,
    PaperworkActionReceipt,
    PaperworkKind,
)
from backend.paperwork.policy import can_read_paperwork
from backend.paperwork.service import PaperworkNotFound
from backend.persistence.models.paperwork import PaperworkRecord


PAPERWORK_ACTIONS = frozenset({"preview", "print", "download_pdf"})


def _record(
    session: Session,
    actor,
    record_id: UUID,
    *,
    expected_kind: PaperworkKind | str | None = None,
) -> PaperworkRecord:
    statement = select(PaperworkRecord).where(PaperworkRecord.id == record_id)
    if expected_kind is not None:
        selected_kind = (
            expected_kind
            if isinstance(expected_kind, PaperworkKind)
            else PaperworkKind(expected_kind)
        )
        statement = statement.where(PaperworkRecord.kind == selected_kind.value)
    record = session.scalar(statement.with_for_update())
    if record is None or not can_read_paperwork(actor, record):
        raise PaperworkNotFound("Paperwork record not found.")
    return record


def _receipt_from_reference(
    session: Session,
    actor,
    reference: dict[str, object],
    *,
    expected_kind: PaperworkKind | str | None = None,
) -> PaperworkActionReceipt:
    try:
        record_id = UUID(str(reference["record_id"]))
        kind = PaperworkKind(str(reference["kind"]))
        revision_number = int(reference["revision_number"])
        action = str(reference["action"])
        recorded = reference["recorded"] is True
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("paperwork action reference is invalid") from None
    record = _record(
        session,
        actor,
        record_id,
        expected_kind=expected_kind,
    )
    if (
        not recorded
        or record.kind != kind.value
        or revision_number < 1
        or record.current_revision_number < revision_number
        or action not in PAPERWORK_ACTIONS
    ):
        raise RuntimeError("paperwork action reference is invalid")
    return PaperworkActionReceipt(
        recorded=True,
        record_id=record_id,
        kind=kind,
        revision_number=revision_number,
        action=action,
    )


def record_paperwork_action(
    session: Session,
    actor,
    *,
    record_id: UUID,
    action: PaperworkAction | str,
    idempotency_key: str,
    request_id: str,
    client_version: str,
    expected_kind: PaperworkKind | str | None = None,
    now: datetime | None = None,
    audit_writer: AuditWriter | None = None,
) -> PaperworkActionReceipt:
    if action not in PAPERWORK_ACTIONS:
        raise ValueError("paperwork action is invalid")
    fixed = now or datetime.now(UTC)
    record = _record(
        session,
        actor,
        record_id,
        expected_kind=expected_kind,
    )
    canonical = {
        "record_id": str(record.id),
        "kind": record.kind,
        "revision_number": record.current_revision_number,
        "action": action,
    }
    claim = claim_idempotency(
        session,
        actor,
        key=idempotency_key,
        action="paperwork.output_action",
        request_sha256=request_digest(canonical),
        now=fixed,
    )
    if claim.replayed:
        return _receipt_from_reference(
            session,
            actor,
            claim.response_reference or {},
            expected_kind=expected_kind,
        )

    details = {
        "record_id": str(record.id),
        "kind": record.kind,
        "revision_number": record.current_revision_number,
        "paperwork_action": action,
    }
    (audit_writer or PostgresAuditWriter()).append(
        session,
        AuditEventInput(
            actor_account_id=actor.account_id,
            actor_staff_member_id=actor.staff_member_id,
            action="paperwork.action_recorded",
            result="success",
            request_id=request_id,
            target_type="paperwork_record",
            target_id=record.id,
            details=details,
            client_version=client_version,
        ),
    )
    complete_idempotency(
        session,
        claim,
        response_status=200,
        response_reference={
            "recorded": True,
            "record_id": str(record.id),
            "kind": record.kind,
            "revision_number": record.current_revision_number,
            "action": action,
        },
        now=fixed,
    )
    session.flush()
    return PaperworkActionReceipt(
        recorded=True,
        record_id=record.id,
        kind=PaperworkKind(record.kind),
        revision_number=record.current_revision_number,
        action=action,
    )
