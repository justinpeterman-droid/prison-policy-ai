from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.persistence.base import Base


class StaffMember(Base):
    __tablename__ = "staff_members"

    id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    employee_number: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    rank: Mapped[str] = mapped_column(String(64), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    shift: Mapped[str] = mapped_column(String(16), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    account: Mapped["Account | None"] = relationship(back_populates="staff_member", uselist=False)


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("role IN ('user','admin')", name="account_role"),
        CheckConstraint("status IN ('active','locked','deactivated')", name="account_status"),
        CheckConstraint("failed_attempts >= 0", name="account_failed_attempts_nonnegative"),
        CheckConstraint("lock_cycle >= 0", name="account_lock_cycle_nonnegative"),
        CheckConstraint("auth_version >= 1", name="account_auth_version_positive"),
        Index("ix_accounts_role_status", "role", "status"),
    )

    id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    staff_member_id: Mapped[UUID] = mapped_column(ForeignKey("staff_members.id", ondelete="RESTRICT"), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")
    pin_hash: Mapped[str] = mapped_column(Text, nullable=False)
    must_change_pin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    temporary_pin_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    lock_cycle: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    auth_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    staff_member: Mapped[StaffMember] = relationship(back_populates="account")
