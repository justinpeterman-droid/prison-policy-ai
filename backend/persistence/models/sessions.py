from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column

from backend.persistence.base import Base


class AccessSession(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        UniqueConstraint("access_token_hash", name="uq_sessions_access_token_hash"),
        UniqueConstraint("renewal_token_hash", name="uq_sessions_renewal_token_hash"),
        Index("ix_sessions_renewal_family", "renewal_family_id"),
        CheckConstraint("octet_length(access_token_hash) = 32", name="session_access_hash_length"),
        CheckConstraint("octet_length(renewal_token_hash) = 32", name="session_renewal_hash_length"),
        CheckConstraint("octet_length(device_id_hash) = 32", name="session_device_hash_length"),
        CheckConstraint("access_expires_at > created_at", name="session_access_expiry_after_create"),
        CheckConstraint(
            "renewal_expires_at > created_at",
            name="session_renewal_expiry_after_create",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    auth_version: Mapped[int] = mapped_column(nullable=False)
    access_token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    access_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    renewal_token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    renewal_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    renewal_family_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    device_id_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    device_label: Mapped[str] = mapped_column(String(120), nullable=False, server_default="")
    persistent: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoke_reason: Mapped[str | None] = mapped_column(String(64))


class RenewalTokenHistory(Base):
    __tablename__ = "renewal_token_history"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_renewal_token_history_token_hash"),
        Index("ix_renewal_history_family", "renewal_family_id", "expires_at"),
        CheckConstraint("octet_length(token_hash) = 32", name="renewal_history_hash_length"),
        CheckConstraint("expires_at > rotated_at", name="renewal_history_expiry_after_rotation"),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    renewal_family_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    rotated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reuse_detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AdminElevation(Base):
    __tablename__ = "admin_elevations"
    __table_args__ = (CheckConstraint("idle_expires_at > issued_at", name="admin_elevation_expiry_after_issue"),)

    session_id: Mapped[UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AdminStepUpToken(Base):
    __tablename__ = "admin_step_up_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_admin_step_up_token_hash"),
        CheckConstraint("octet_length(token_hash) = 32", name="admin_step_up_hash_length"),
        CheckConstraint(
            "purpose IN ('staff_write','account_create','account_role_status','account_reset_pin','account_unlock','account_revoke_sessions','report_restore','report_transfer','bulk_export','audit_export','review_lab_handoff')",
            name="admin_step_up_purpose",
        ),
        CheckConstraint("expires_at > issued_at", name="admin_step_up_expiry_after_issue"),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
