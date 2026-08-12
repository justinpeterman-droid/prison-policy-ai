from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.persistence.models.security import IdempotencyRecord


IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
FORBIDDEN_REFERENCE_KEYS = {
    "access_token", "renewal_token", "temporary_pin", "pin", "step_up_token",
    "report_text", "field_notes",
}


class IdempotencyConflict(ValueError):
    code = "idempotency_conflict"


class RequestInProgress(ValueError):
    code = "request_in_progress"


@dataclass(frozen=True)
class IdempotencyClaim:
    record_id: UUID
    replayed: bool
    response_status: int | None
    response_reference: dict[str, object] | None


def request_digest(payload: object) -> bytes:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).digest()


def _safe_reference(value: object) -> bool:
    if isinstance(value, dict):
        return not (set(value) & FORBIDDEN_REFERENCE_KEYS) and all(
            _safe_reference(item) for item in value.values()
        )
    if isinstance(value, list):
        return all(_safe_reference(item) for item in value)
    return value is None or isinstance(value, (str, int, float, bool))


def claim_idempotency(
    session: Session,
    actor,
    *,
    key: str,
    action: str,
    request_sha256: bytes,
    now: datetime,
) -> IdempotencyClaim:
    if not isinstance(key, str) or not IDEMPOTENCY_KEY_PATTERN.fullmatch(key):
        raise ValueError("idempotency key is invalid")
    if not isinstance(request_sha256, bytes) or len(request_sha256) != 32:
        raise ValueError("request SHA-256 is invalid")
    inserted_id = session.execute(
        insert(IdempotencyRecord)
        .values(
            actor_account_id=actor.account_id,
            action=action,
            idempotency_key=key,
            request_sha256=request_sha256,
            status="in_progress",
            response_reference={},
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        .on_conflict_do_nothing(
            index_elements=[
                IdempotencyRecord.actor_account_id,
                IdempotencyRecord.action,
                IdempotencyRecord.idempotency_key,
            ]
        )
        .returning(IdempotencyRecord.id)
    ).scalar_one_or_none()
    if inserted_id is not None:
        return IdempotencyClaim(inserted_id, False, None, None)

    record = session.scalar(
        select(IdempotencyRecord)
        .where(
            IdempotencyRecord.actor_account_id == actor.account_id,
            IdempotencyRecord.action == action,
            IdempotencyRecord.idempotency_key == key,
        )
        .with_for_update()
    )
    if record is None:
        raise RuntimeError("idempotency claim disappeared after a uniqueness conflict")
    if record.expires_at <= now:
        record.request_sha256 = request_sha256
        record.status = "in_progress"
        record.response_status = None
        record.response_reference = {}
        record.created_at = now
        record.completed_at = None
        record.expires_at = now + timedelta(hours=24)
        session.flush()
        return IdempotencyClaim(record.id, False, None, None)
    if record.request_sha256 != request_sha256:
        raise IdempotencyConflict("The idempotency key was used for another request.")
    if record.status == "completed":
        return IdempotencyClaim(
            record.id, True, record.response_status, dict(record.response_reference),
        )
    raise RequestInProgress("The idempotent operation is already in progress.")


def complete_idempotency(
    session: Session,
    claim: IdempotencyClaim,
    *,
    response_status: int,
    response_reference: dict[str, object],
    now: datetime,
) -> None:
    if claim.replayed:
        return
    if not isinstance(response_reference, dict) or not _safe_reference(response_reference):
        raise ValueError("idempotency response reference is invalid")
    encoded = json.dumps(response_reference, sort_keys=True, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > 4096:
        raise ValueError("idempotency response reference is too large")
    record = session.scalar(
        select(IdempotencyRecord).where(IdempotencyRecord.id == claim.record_id).with_for_update()
    )
    if record is None or record.status != "in_progress":
        raise RuntimeError("idempotency claim is unavailable")
    record.status = "completed"
    record.response_status = response_status
    record.response_reference = dict(response_reference)
    record.completed_at = now
    session.flush()
