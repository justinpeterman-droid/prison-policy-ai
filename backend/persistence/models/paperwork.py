"""Persistence mappings for revisioned operational paperwork."""
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column

from backend.persistence.base import Base


PAPERWORK_KIND_VALUES = (
    "'count_sheet','assignment_roster','uniform_inspection',"
    "'metal_detector_test','perimeter_check','random_search_log',"
    "'detector_sign_out'"
)
PAPERWORK_REVISION_REASON_VALUES = (
    "'autosave','manual_save','recovery','restored'"
)


class PaperworkRecord(Base):
    """Current authorized view of one operational-paperwork record."""

    __tablename__ = "paperwork_records"
    __table_args__ = (
        CheckConstraint(
            f"kind IN ({PAPERWORK_KIND_VALUES})",
            name="kind",
        ),
        CheckConstraint(
            "current_revision_number >= 1",
            name="current_revision_positive",
        ),
        Index(
            "ix_paperwork_records_kind_date_shift",
            "kind",
            "work_date",
            "shift",
            "id",
        ),
        Index(
            "ix_paperwork_records_creator_updated",
            "created_by_staff_member_id",
            "updated_at",
            "id",
        ),
        Index(
            "ix_paperwork_records_updated",
            "updated_at",
            "id",
        ),
        Index(
            "uq_paperwork_records_daily_date_shift",
            "kind",
            "work_date",
            "shift",
            unique=True,
            postgresql_where=text("kind <> 'count_sheet'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift: Mapped[str | None] = mapped_column(String(32))
    current_revision_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="1",
    )
    current_payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_by_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_by_staff_member_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff_members.id", ondelete="RESTRICT"),
        nullable=False,
    )
    last_editor_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    last_editor_staff_member_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff_members.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class PaperworkRevision(Base):
    """Immutable content snapshot for one paperwork save or restore."""

    __tablename__ = "paperwork_revisions"
    __table_args__ = (
        UniqueConstraint(
            "record_id",
            "revision_number",
            name="uq_paperwork_revisions_record_number",
        ),
        CheckConstraint(
            "revision_number >= 1",
            name="revision_number_positive",
        ),
        CheckConstraint(
            f"reason IN ({PAPERWORK_REVISION_REASON_VALUES})",
            name="reason",
        ),
        Index(
            "ix_paperwork_revisions_record_created",
            "record_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    record_id: Mapped[UUID] = mapped_column(
        ForeignKey("paperwork_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    editor_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    editor_staff_member_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff_members.id", ondelete="RESTRICT"),
        nullable=False,
    )
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    changed_fields: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    client_version: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
