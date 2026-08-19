import enum
from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column

from backend.persistence.base import Base


class ReportStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ReportType(str, enum.Enum):
    FIRST_PERSON = "first_person"
    SUPERVISOR_SUMMARY = "supervisor_summary"
    COVER_LETTER = "cover_letter"
    DISCIPLINARY = "disciplinary"
    INVESTIGATION = "investigation"
    FORM_005 = "form_005"


class RevisionReason(str, enum.Enum):
    AUTOSAVE = "autosave"
    MANUAL_SAVE = "manual_save"
    AI_RESULT = "ai_result"
    RESTORED = "restored"
    STATUS_CHANGE = "status_change"
    OWNERSHIP_CHANGE = "ownership_change"
    RECOVERY = "recovery"
    ADMIN_EDIT = "admin_edit"


STATUS_VALUES = "'in_progress','completed','archived'"
INCIDENT_REASON_VALUES = (
    "'autosave','manual_save','ai_result','restored','status_change',"
    "'ownership_change','recovery'"
)
REPORT_REASON_VALUES = (
    "'autosave','manual_save','ai_result','restored','status_change',"
    "'ownership_change','recovery','admin_edit'"
)


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(f"status IN ({STATUS_VALUES})", name="status"),
        CheckConstraint("current_revision_number >= 0", name="current_revision_nonnegative"),
        Index("ix_incidents_status_date", "status", "incident_date", "id"),
        Index("ix_incidents_category_date", "category", "incident_date", "id"),
        Index("ix_incidents_updated_at", "updated_at", "id"),
        Index(
            "uq_incidents_incident_number",
            "incident_number",
            unique=True,
            postgresql_where=text("incident_number IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    created_by_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False,
    )
    created_by_staff_member_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff_members.id", ondelete="RESTRICT"), nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="in_progress",
    )
    current_revision_number: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0",
    )
    incident_number: Mapped[str | None] = mapped_column(String(11))
    incident_name: Mapped[str | None] = mapped_column(String(160))
    incident_date: Mapped[date | None] = mapped_column(Date)
    incident_time: Mapped[time | None] = mapped_column(Time)
    facility: Mapped[str | None] = mapped_column(String(120))
    shift: Mapped[str | None] = mapped_column(String(32))
    location: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(120))
    field_notes: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    classification: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    extracted_facts: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    gap_answers: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    charges: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb"),
    )
    validation: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IncidentRevision(Base):
    __tablename__ = "incident_revisions"
    __table_args__ = (
        UniqueConstraint(
            "incident_id", "revision_number",
            name="uq_incident_revisions_parent_number",
        ),
        CheckConstraint("revision_number >= 0", name="number_nonnegative"),
        CheckConstraint(f"reason IN ({INCIDENT_REASON_VALUES})", name="reason"),
        Index("ix_incident_revisions_parent_created", "incident_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    incident_id: Mapped[UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    editor_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False,
    )
    editor_staff_member_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff_members.id", ondelete="RESTRICT"), nullable=False,
    )
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    changed_fields: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    client_version: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint(
            "incident_id", "report_type", "reporting_staff_member_id",
            name="uq_reports_incident_type_owner",
        ),
        CheckConstraint(f"status IN ({STATUS_VALUES})", name="status"),
        CheckConstraint("current_revision_number >= 0", name="current_revision_nonnegative"),
        Index("ix_reports_incident", "incident_id", "id"),
        Index("ix_reports_status_updated", "status", "updated_at", "id"),
        Index("ix_reports_owner_updated", "reporting_staff_member_id", "updated_at", "id"),
        Index("ix_reports_preparer_updated", "prepared_by_staff_member_id", "updated_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    incident_id: Mapped[UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=False,
    )
    report_type: Mapped[ReportType] = mapped_column(
        Enum(
            ReportType, name="report_type", native_enum=True,
            values_callable=lambda members: [member.value for member in members],
        ),
        nullable=False,
    )
    reporting_staff_member_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff_members.id", ondelete="RESTRICT"), nullable=False,
    )
    prepared_by_staff_member_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff_members.id", ondelete="RESTRICT"), nullable=False,
    )
    created_by_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="in_progress",
    )
    current_revision_number: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0",
    )
    current_content: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReportAccess(Base):
    __tablename__ = "report_access"
    __table_args__ = (
        CheckConstraint("relationship IN ('owner','preparer')", name="relationship"),
        Index("ix_report_access_staff_relationship", "staff_member_id", "relationship", "report_id"),
    )

    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="RESTRICT"), primary_key=True,
    )
    staff_member_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff_members.id", ondelete="RESTRICT"), primary_key=True,
    )
    relationship: Mapped[str] = mapped_column(String(16), nullable=False)
    granted_by_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReportRevision(Base):
    __tablename__ = "report_revisions"
    __table_args__ = (
        UniqueConstraint(
            "report_id", "revision_number",
            name="uq_report_revisions_parent_number",
        ),
        CheckConstraint("revision_number >= 0", name="number_nonnegative"),
        CheckConstraint(f"reason IN ({REPORT_REASON_VALUES})", name="reason"),
        Index("ix_report_revisions_parent_created", "report_id", "created_at"),
        Index("ix_report_revisions_editor_created", "editor_staff_member_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="RESTRICT"), nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    editor_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False,
    )
    editor_staff_member_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff_members.id", ondelete="RESTRICT"), nullable=False,
    )
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    changed_fields: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    source_incident_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "incident_revisions.id", ondelete="SET NULL",
            name="fk_report_revisions_source_incident_revision",
        ),
    )
    source_ai_job_id: Mapped[UUID | None] = mapped_column(UUIDType(as_uuid=True))
    provenance: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    fast_model: Mapped[str | None] = mapped_column(String(120))
    pro_model: Mapped[str | None] = mapped_column(String(120))
    model_location: Mapped[str | None] = mapped_column(String(64))
    classification_prompt_sha256: Mapped[str | None] = mapped_column(String(64))
    generation_prompt_sha256: Mapped[str | None] = mapped_column(String(64))
    checklist_sha256: Mapped[str | None] = mapped_column(String(64))
    template_sha256: Mapped[str | None] = mapped_column(String(64))
    cloud_run_revision: Mapped[str | None] = mapped_column(String(128))
    source_commit: Mapped[str | None] = mapped_column(String(128))
    client_version: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
