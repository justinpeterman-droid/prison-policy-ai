"""Browser-only bindings layered on the existing opaque identity sessions."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, LargeBinary, func
from sqlalchemy.dialects.postgresql import UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column

from backend.persistence.base import Base


class BrowserSessionBinding(Base):
    """Binds one Access session to a browser CSRF secret digest.

    Authentication credentials remain in the existing ``sessions`` table. This
    table stores only the digest required to validate same-origin browser
    mutations; the readable token is returned once in a non-HttpOnly cookie.
    """

    __tablename__ = "browser_session_bindings"
    __table_args__ = (
        CheckConstraint(
            "octet_length(csrf_token_hash) = 32",
            name="browser_csrf_hash_length",
        ),
    )

    session_id: Mapped[UUID] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    csrf_token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    rotated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
