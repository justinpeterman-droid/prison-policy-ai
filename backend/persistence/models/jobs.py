"""Durable AI job, transactional outbox, and export records (RP-06).

These tables persist only stable IDs, digests, status, and error
*categories* -- never raw authorization headers, field notes/report text,
prompt/response content, or secrets. `AiJob.request`/`result` are bounded
JSONB columns that the service layer only ever populates with safe scalars
(e.g. `base_revision_number`); the report engine's actual notes/prompts never
pass through this module.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column

from backend.persistence.base import Base


#: Mirrors AUDIT_ENUM_FIELDS["job_type"] in backend.identity.audit exactly.
AI_JOB_TYPES = ("classify", "extract", "generate", "disciplinary")
#: `AiJob.state`: the coarse lifecycle state.
AI_JOB_STATES = ("queued", "running", "succeeded", "failed", "cancelled")
#: `AiJob.stage`: the stable progress stage Access polls and displays.
AI_JOB_STAGES = (
    "queued", "classifying", "extracting", "validating", "generating",
    "disciplinary", "completed", "failed",
)
#: `TaskOutbox.state`: outbox row lifecycle (RP-06 persists; RP-07 drains).
TASK_OUTBOX_STATES = ("pending", "dispatched", "completed", "failed")

_AI_JOB_TYPE_VALUES = "'" + "','".join(AI_JOB_TYPES) + "'"
_AI_JOB_STATE_VALUES = "'" + "','".join(AI_JOB_STATES) + "'"
_AI_JOB_STAGE_VALUES = "'" + "','".join(AI_JOB_STAGES) + "'"
_TASK_OUTBOX_STATE_VALUES = "'" + "','".join(TASK_OUTBOX_STATES) + "'"


class AiJob(Base):
    __tablename__ = "ai_jobs"
    __table_args__ = (
        UniqueConstraint(
            "requested_by_account_id", "idempotency_key",
            name="uq_ai_jobs_actor_idempotency_key",
        ),
        CheckConstraint(f"job_type IN ({_AI_JOB_TYPE_VALUES})", name="job_type"),
        CheckConstraint(f"state IN ({_AI_JOB_STATE_VALUES})", name="state"),
        CheckConstraint(f"stage IN ({_AI_JOB_STAGE_VALUES})", name="stage"),
        CheckConstraint("attempt_count >= 0", name="attempt_count_nonnegative"),
        CheckConstraint(
            "expected_incident_revision_number >= 0",
            name="expected_incident_revision_nonnegative",
        ),
        CheckConstraint(
            "octet_length(request_sha256) = 32", name="ai_jobs_request_hash_length",
        ),
        Index("ix_ai_jobs_queue_state", "state", "created_at"),
        Index("ix_ai_jobs_requested_actor", "requested_by_account_id", "created_at"),
        Index("ix_ai_jobs_incident", "incident_id", "created_at"),
        Index("ix_ai_jobs_report", "report_id", "created_at"),
        Index("ix_ai_jobs_expiry", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    incident_id: Mapped[UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=False,
    )
    report_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("reports.id", ondelete="RESTRICT"),
    )
    requested_by_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False,
    )
    job_type: Mapped[str] = mapped_column(String(16), nullable=False)
    state: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="queued",
    )
    stage: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="queued",
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_sha256: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0",
    )
    #: Bounded, safe scalars only (e.g. base_revision_number) -- never notes/prompts.
    request: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    #: Populated by RP-07; bounded, safe scalars only -- never raw provider output.
    result: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    #: A stable error *category*, never a provider message or stack trace.
    error_code: Mapped[str | None] = mapped_column(String(64))
    #: The incident revision this job was queued against; guards stale results.
    expected_incident_revision_number: Mapped[int] = mapped_column(
        Integer, nullable=False,
    )
    fast_model: Mapped[str | None] = mapped_column(String(120))
    pro_model: Mapped[str | None] = mapped_column(String(120))
    model_location: Mapped[str | None] = mapped_column(String(64))
    prompt_sha256: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TaskOutbox(Base):
    __tablename__ = "task_outbox"
    __table_args__ = (
        UniqueConstraint("ai_job_id", name="uq_task_outbox_ai_job"),
        CheckConstraint(f"state IN ({_TASK_OUTBOX_STATE_VALUES})", name="state"),
        CheckConstraint("attempts >= 0", name="attempts_nonnegative"),
        Index("ix_task_outbox_queue_state", "state", "available_at"),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    ai_job_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_jobs.id", ondelete="CASCADE"), nullable=False,
    )
    state: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="pending",
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: A stable error *category*, never a provider message or stack trace.
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )


class Export(Base):
    __tablename__ = "exports"
    __table_args__ = (
        CheckConstraint("byte_length >= 0", name="byte_length_nonnegative"),
        CheckConstraint(
            "octet_length(output_sha256) = 32", name="exports_output_hash_length",
        ),
        Index("ix_exports_report", "report_id", "created_at"),
        Index("ix_exports_report_revision", "report_revision_id"),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="RESTRICT"), nullable=False,
    )
    report_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("report_revisions.id", ondelete="RESTRICT"), nullable=False,
    )
    exported_by_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False,
    )
    template_version: Mapped[str] = mapped_column(String(64), nullable=False)
    output_sha256: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    byte_length: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    download_name: Mapped[str] = mapped_column(String(255), nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
