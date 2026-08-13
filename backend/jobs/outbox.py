"""Transactional outbox row lifecycle for durable AI job dispatch (RP-06).

This module only persists `task_outbox` row creation and state transitions
inside the caller's transaction. Dispatch-side concerns -- the actual Cloud
Tasks call -- are out of scope here; RP-07's dispatcher/worker drains this
outbox later.
"""
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.persistence.models.jobs import TaskOutbox


#: Outbox states RP-07's dispatcher will never revisit once reached.
TERMINAL_OUTBOX_STATES = frozenset({"completed", "failed"})


def create_outbox_row(
    session: Session, ai_job_id: UUID, *, now: datetime | None = None,
) -> TaskOutbox:
    """Append one pending outbox row for a just-created job.

    Caller-owned transaction: this only adds and flushes, it never commits,
    so it lands in the same atomic unit as the job insert, idempotency
    completion, and audit write.
    """
    fixed = now or datetime.now(UTC)
    row = TaskOutbox(
        id=uuid4(), ai_job_id=ai_job_id, state="pending", attempts=0,
        available_at=fixed, created_at=fixed,
    )
    session.add(row)
    session.flush()
    return row


def claim_outbox_row(session: Session, ai_job_id: UUID) -> TaskOutbox | None:
    """Lock the one pending outbox row for a job, or return None if unavailable.

    Uses `FOR UPDATE SKIP LOCKED` so a concurrent claimer never blocks on --
    or double-processes -- the same row; it simply sees no pending row to
    claim.
    """
    return session.execute(
        select(TaskOutbox)
        .where(TaskOutbox.ai_job_id == ai_job_id, TaskOutbox.state == "pending")
        .with_for_update(skip_locked=True)
    ).scalar_one_or_none()


def mark_outbox_dispatched(row: TaskOutbox, *, now: datetime | None = None) -> None:
    fixed = now or datetime.now(UTC)
    row.state = "dispatched"
    row.attempts += 1
    row.dispatched_at = fixed


def mark_outbox_terminal(
    row: TaskOutbox, state: str, *, error_code: str | None = None,
) -> None:
    if state not in TERMINAL_OUTBOX_STATES:
        raise ValueError("outbox terminal state is invalid")
    row.state = state
    row.last_error_code = error_code


__all__ = [
    "TERMINAL_OUTBOX_STATES",
    "claim_outbox_row",
    "create_outbox_row",
    "mark_outbox_dispatched",
    "mark_outbox_terminal",
]
