"""Caller-transaction-owned creation of Cloud Tasks outbox intents."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from backend.persistence.models.jobs import TaskOutbox


def enqueue_job(session: Session, job_id: UUID, *, now: datetime) -> TaskOutbox:
    """Add exactly one pending dispatch intent without making a network call."""
    row = TaskOutbox(
        id=uuid4(),
        ai_job_id=job_id,
        state="pending",
        attempts=0,
        available_at=now,
        created_at=now,
    )
    session.add(row)
    return row
