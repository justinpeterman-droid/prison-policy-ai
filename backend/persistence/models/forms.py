"""Persistence mappings for incident paperwork packets and document actions."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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


OUTPUT_KIND_VALUES = "'digital_document','physical_only'"
PACKET_GROUP_VALUES = "'required','recommended','additional'"
PACKET_STATE_VALUES = "'selected','not_applicable','removed'"
COMPLETENESS_VALUES = "'ready','needs_review','missing_information'"
DOCUMENT_ACTION_VALUES = (
    "'preview','print','download_word','download_pdf','copy_text'"
)


class FormTemplate(Base):
    __tablename__ = "form_templates"
    __table_args__ = (
        UniqueConstraint("code", name="uq_form_templates_code"),
        CheckConstraint(
            f"output_kind IN ({OUTPUT_KIND_VALUES})",
            name="output_kind",
        ),
        Index("ix_form_templates_active_category", "active", "category", "code"),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    output_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    revision_label: Mapped[str | None] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    definition: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
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


class IncidentPacketItem(Base):
    __tablename__ = "incident_packet_items"
    __table_args__ = (
        Index(
            "uq_packet_items_global_template",
            "incident_id",
            "form_template_id",
            unique=True,
            postgresql_where=text("reporting_staff_member_id IS NULL"),
        ),
        Index(
            "uq_packet_items_officer_template",
            "incident_id",
            "form_template_id",
            "reporting_staff_member_id",
            unique=True,
            postgresql_where=text("reporting_staff_member_id IS NOT NULL"),
        ),
        CheckConstraint(
            f"packet_group IN ({PACKET_GROUP_VALUES})",
            name="packet_group",
        ),
        CheckConstraint(
            f"packet_state IN ({PACKET_STATE_VALUES})",
            name="packet_state",
        ),
        CheckConstraint(
            "source_incident_revision_number >= 0",
            name="source_revision_nonnegative",
        ),
        Index(
            "ix_incident_packet_items_incident_group",
            "incident_id",
            "packet_group",
            "packet_state",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    incident_id: Mapped[UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
    )
    form_template_id: Mapped[UUID] = mapped_column(
        ForeignKey("form_templates.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reporting_staff_member_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff_members.id", ondelete="RESTRICT"),
    )
    packet_group: Mapped[str] = mapped_column(String(16), nullable=False)
    packet_state: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default="selected",
    )
    source_incident_revision_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    selection_reason: Mapped[str | None] = mapped_column(String(240))
    not_applicable_reason: Mapped[str | None] = mapped_column(String(500))
    added_by_account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"),
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


class FormInstance(Base):
    __tablename__ = "form_instances"
    __table_args__ = (
        UniqueConstraint(
            "packet_item_id",
            name="uq_form_instances_packet_item_id",
        ),
        CheckConstraint(
            "source_incident_revision_number >= 0",
            name="source_revision_nonnegative",
        ),
        CheckConstraint(
            f"completeness IN ({COMPLETENESS_VALUES})",
            name="completeness",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    packet_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("incident_packet_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_incident_revision_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    populated_fields: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    manual_fields: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    completeness: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="missing_information",
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


class PhysicalPaperworkAcknowledgment(Base):
    __tablename__ = "physical_paperwork_acknowledgments"
    __table_args__ = (
        UniqueConstraint(
            "packet_item_id",
            name="uq_physical_paperwork_acknowledgments_packet_item_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    packet_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("incident_packet_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    acknowledged_by_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    acknowledged_by_staff_member_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff_members.id", ondelete="RESTRICT"),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(String(500))
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DocumentActionEvent(Base):
    __tablename__ = "document_action_events"
    __table_args__ = (
        CheckConstraint(
            f"action IN ({DOCUMENT_ACTION_VALUES})",
            name="action",
        ),
        CheckConstraint(
            "incident_revision_number >= 0",
            name="incident_revision_nonnegative",
        ),
        Index(
            "ix_document_action_events_incident_created",
            "incident_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    incident_id: Mapped[UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
    )
    packet_item_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("incident_packet_items.id", ondelete="SET NULL"),
    )
    report_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("reports.id", ondelete="SET NULL"),
    )
    actor_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    actor_staff_member_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff_members.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    incident_revision_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    details: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
