"""Durable, metadata-only AI job, outbox, and export mappings."""

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
from sqlalchemy.orm import validates

from backend.persistence.base import Base


JOB_TYPES = "'classify','extract','generate','disciplinary'"
JOB_STATES = "'queued','running','succeeded','failed','cancelled'"
JOB_STAGES = (
    "'queued','classifying','extracting','validating','generating',"
    "'disciplinary','completed','failed'"
)
RESULT_REFERENCE_KEYS = frozenset({"incident_revision_number", "reports"})
RESULT_REPORT_REFERENCE_KEYS = frozenset({"report_id", "revision_number"})
MAX_RESULT_REPORT_REFERENCES = 20


class InvalidJobResultReference(ValueError):
    """A worker supplied data outside the durable public result contract."""

    code = "job_result_invalid"


def normalize_job_result_reference(value: object) -> dict[str, object]:
    """Return the closed metadata-only result shape accepted by storage/API."""
    if type(value) is not dict or not set(value).issubset(RESULT_REFERENCE_KEYS):
        raise InvalidJobResultReference("job result reference is invalid")

    normalized: dict[str, object] = {}
    if "incident_revision_number" in value:
        revision_number = value["incident_revision_number"]
        if type(revision_number) is not int or revision_number < 1:
            raise InvalidJobResultReference("job result reference is invalid")
        normalized["incident_revision_number"] = revision_number

    if "reports" in value:
        reports = value["reports"]
        if type(reports) is not list or len(reports) > MAX_RESULT_REPORT_REFERENCES:
            raise InvalidJobResultReference("job result reference is invalid")
        normalized_reports: list[dict[str, object]] = []
        seen_report_ids: set[UUID] = set()
        for item in reports:
            if type(item) is not dict or set(item) != RESULT_REPORT_REFERENCE_KEYS:
                raise InvalidJobResultReference("job result reference is invalid")
            raw_report_id = item["report_id"]
            revision_number = item["revision_number"]
            if type(raw_report_id) is not str or type(revision_number) is not int:
                raise InvalidJobResultReference("job result reference is invalid")
            try:
                report_id = UUID(raw_report_id)
            except ValueError:
                raise InvalidJobResultReference("job result reference is invalid") from None
            if revision_number < 1 or report_id in seen_report_ids:
                raise InvalidJobResultReference("job result reference is invalid")
            seen_report_ids.add(report_id)
            normalized_reports.append({
                "report_id": str(report_id),
                "revision_number": revision_number,
            })
        normalized["reports"] = sorted(
            normalized_reports, key=lambda item: str(item["report_id"]),
        )
    return normalized


class AiJob(Base):
    """A durable job control record; content remains in report revisions."""

    __tablename__ = "ai_jobs"
    __table_args__ = (
        CheckConstraint(f"job_type IN ({JOB_TYPES})", name="job_type"),
        CheckConstraint(f"state IN ({JOB_STATES})", name="state"),
        CheckConstraint(f"stage IN ({JOB_STAGES})", name="stage"),
        CheckConstraint("base_incident_revision >= 1", name="base_revision_positive"),
        CheckConstraint("attempts >= 0", name="attempts_nonnegative"),
        CheckConstraint(
            "octet_length(request_sha256) = 32", name="request_hash_length",
        ),
        CheckConstraint(
            "octet_length(request_metadata::text) <= 4096",
            name="request_metadata_size",
        ),
        CheckConstraint(
            "octet_length(result_reference::text) <= 4096",
            name="result_reference_size",
        ),
        CheckConstraint(
            "jsonb_typeof(result_reference) = 'object'",
            name="result_reference_object",
        ),
        CheckConstraint(
            "(result_reference - 'incident_revision_number' - 'reports') = '{}'::jsonb",
            name="result_reference_keys",
        ),
        CheckConstraint(
            "CASE WHEN result_reference ? 'incident_revision_number' THEN "
            "jsonb_typeof(result_reference->'incident_revision_number') = 'number' "
            "AND (result_reference->>'incident_revision_number') ~ '^[1-9][0-9]*$' "
            "ELSE TRUE END",
            name="result_reference_incident_revision",
        ),
        CheckConstraint(
            "CASE WHEN result_reference ? 'reports' THEN CASE WHEN "
            "jsonb_typeof(result_reference->'reports') = 'array' THEN "
            "jsonb_array_length(result_reference->'reports') <= 20 "
            "AND NOT jsonb_path_exists(result_reference, "
            "'$.reports[*] ? (@.type() != \"object\")') "
            "AND NOT jsonb_path_exists(result_reference, "
            "'$.reports[*] ? (!exists(@.report_id) || !exists(@.revision_number))') "
            "AND NOT jsonb_path_exists(result_reference, "
            "'$.reports[*].keyvalue() ? "
            "(@.key != \"report_id\" && @.key != \"revision_number\")') "
            "AND NOT jsonb_path_exists(result_reference, "
            "'$.reports[*] ? (@.report_id.type() != \"string\" || "
            "@.revision_number.type() != \"number\")') "
            "AND NOT jsonb_path_exists(result_reference, "
            "'$.reports[*] ? (!(@.report_id like_regex "
            "\"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
            "[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$\"))') "
            "AND NOT jsonb_path_exists(result_reference, "
            "'$.reports[*] ? (!(@.revision_number.string() like_regex "
            "\"^[1-9][0-9]*$\"))') ELSE FALSE END ELSE TRUE END",
            name="result_reference_reports",
        ),
        CheckConstraint(
            "((state = 'running') = "
            "(lease_expires_at IS NOT NULL AND claim_token IS NOT NULL))",
            name="lease_matches_running_state",
        ),
        CheckConstraint(
            "lease_expires_at IS NULL OR started_at IS NOT NULL",
            name="lease_requires_start",
        ),
        CheckConstraint(
            "error_code IS NULL OR error_code ~ '^[a-z][a-z0-9_]{0,63}$'",
            name="error_code_format",
        ),
        Index("ix_ai_jobs_queue", "state", "created_at", "id"),
        Index(
            "ix_ai_jobs_claim", "state", "lease_expires_at", "created_at", "id",
        ),
        Index(
            "ix_ai_jobs_requested_actor", "requested_by_account_id", "created_at", "id",
        ),
        Index("ix_ai_jobs_incident", "incident_id", "created_at", "id"),
        Index("ix_ai_jobs_report", "report_id", "created_at", "id"),
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
    job_type: Mapped[str] = mapped_column(String(24), nullable=False)
    state: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="queued",
    )
    stage: Mapped[str] = mapped_column(
        String(24), nullable=False, server_default="queued",
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_sha256: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    base_incident_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claim_token: Mapped[UUID | None] = mapped_column(UUIDType(as_uuid=True))
    request_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    result_reference: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    error_code: Mapped[str | None] = mapped_column(String(64))
    fast_model: Mapped[str | None] = mapped_column(String(120))
    pro_model: Mapped[str | None] = mapped_column(String(120))
    model_location: Mapped[str | None] = mapped_column(String(64))
    classification_prompt_sha256: Mapped[str | None] = mapped_column(String(64))
    generation_prompt_sha256: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @validates("result_reference")
    def _validate_result_reference(self, _key: str, value: object) -> dict[str, object]:
        return normalize_job_result_reference(value)


class TaskOutbox(Base):
    """One after-commit Cloud Tasks dispatch intent per AI job."""

    __tablename__ = "task_outbox"
    __table_args__ = (
        UniqueConstraint("ai_job_id", name="uq_task_outbox_ai_job_id"),
        CheckConstraint(
            "state IN ('pending','dispatched','failed')", name="state",
        ),
        CheckConstraint("attempts >= 0", name="attempts_nonnegative"),
        CheckConstraint(
            "last_error_code IS NULL OR "
            "last_error_code ~ '^[a-z][a-z0-9_]{0,63}$'",
            name="last_error_code_format",
        ),
        Index("ix_task_outbox_available", "state", "available_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    ai_job_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_jobs.id", ondelete="RESTRICT"), nullable=False,
    )
    state: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="pending",
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )


class Export(Base):
    """Metadata for a revision-exact transient export; never document bytes."""

    __tablename__ = "exports"
    __table_args__ = (
        CheckConstraint(
            "octet_length(output_sha256) = 32", name="output_hash_length",
        ),
        CheckConstraint("size_bytes >= 0", name="size_nonnegative"),
        Index("ix_exports_report_revision", "report_id", "report_revision_id", "id"),
        Index(
            "ix_exports_actor_created", "exported_by_account_id", "created_at", "id",
        ),
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
    template_version: Mapped[str] = mapped_column(String(128), nullable=False)
    output_sha256: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    download_name: Mapped[str] = mapped_column(String(255), nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
