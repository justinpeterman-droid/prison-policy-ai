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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column

from backend.persistence.base import Base


class BrowserHandoff(Base):
    __tablename__ = "browser_handoffs"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_browser_handoffs_token_hash"),
        CheckConstraint("purpose = 'review_lab'", name="browser_handoff_purpose"),
        CheckConstraint(
            "octet_length(token_hash) = 32", name="browser_handoff_hash_length"
        ),
        CheckConstraint(
            "expires_at > created_at", name="browser_handoff_expiry_after_create"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class BrowserSession(Base):
    __tablename__ = "browser_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_browser_sessions_token_hash"),
        CheckConstraint("purpose = 'review_lab'", name="browser_session_purpose"),
        CheckConstraint(
            "octet_length(token_hash) = 32", name="browser_session_hash_length"
        ),
        CheckConstraint(
            "expires_at > created_at", name="browser_session_expiry_after_create"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    issuing_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthRateLimit(Base):
    __tablename__ = "auth_rate_limits"
    __table_args__ = (
        UniqueConstraint(
            "dimension", "subject_hash", name="uq_auth_rate_limit_dimension_subject"
        ),
        CheckConstraint(
            "octet_length(subject_hash) = 32",
            name="auth_rate_limit_subject_hash_length",
        ),
        CheckConstraint(
            "dimension IN ('employee','device','network')",
            name="auth_rate_limit_dimension",
        ),
        CheckConstraint("hit_count >= 0", name="auth_rate_limit_hit_count_nonnegative"),
        Index("ix_auth_rate_limits_window", "dimension", "window_started_at"),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint(
            "result IN ('success','denied','failed')", name="audit_event_result"
        ),
        CheckConstraint(
            "device_id_hash IS NULL OR octet_length(device_id_hash) = 32",
            name="audit_event_device_hash_length",
        ),
        CheckConstraint(
            "network_hash IS NULL OR octet_length(network_hash) = 32",
            name="audit_event_network_hash_length",
        ),
        CheckConstraint(
            "octet_length(details::text) <= 4096", name="audit_event_details_size"
        ),
        Index("ix_audit_events_occurred_action", "occurred_at", "action"),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    actor_account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL")
    )
    actor_staff_member_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff_members.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[UUID | None] = mapped_column(UUIDType(as_uuid=True))
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_version: Mapped[str | None] = mapped_column(String(64))
    device_id_hash: Mapped[bytes | None] = mapped_column(LargeBinary(32))
    network_hash: Mapped[bytes | None] = mapped_column(LargeBinary(32))
    details: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "actor_account_id",
            "action",
            "idempotency_key",
            name="uq_idempotency_actor_action_key",
        ),
        CheckConstraint(
            "status IN ('in_progress','completed')",
            name="idempotency_status",
        ),
        CheckConstraint(
            "octet_length(request_sha256) = 32",
            name="idempotency_request_hash_length",
        ),
        CheckConstraint(
            "octet_length(response_reference::text) <= 4096",
            name="idempotency_response_reference_size",
        ),
        Index("ix_idempotency_expiry", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    actor_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_sha256: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_reference: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
