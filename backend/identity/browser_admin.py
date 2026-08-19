"""Browser-specific administrator elevation helpers.

The existing identity elevation service remains the authority for PIN
confirmation and one-use step-up tokens.  This module only adapts that service
to the cookie-authenticated Guided Operations browser surface.
"""
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.identity.audit import AuditWriter
from backend.identity.elevation import (
    STEP_UP_PURPOSES,
    AdminElevationRequired,
    StepUpRequired,
    confirm_admin_pin,
    consume_step_up,
    touch_admin_elevation,
)
from backend.persistence.models.sessions import AdminElevation


class BrowserAdminStepUpRequired(PermissionError):
    code = "step_up_required"


@dataclass(frozen=True)
class BrowserAdminState:
    elevated: bool
    elevation_expires_at: datetime | None


@dataclass(frozen=True)
class BrowserAdminStepUp:
    raw_token: str
    expires_at: datetime
    purpose: str


def _require_admin(actor) -> None:
    if getattr(actor, "role", None) != "admin":
        raise PermissionError("Administrator access is required.")


def browser_admin_state(
    session: Session,
    *,
    actor,
    now: datetime,
) -> BrowserAdminState:
    _require_admin(actor)
    row = session.scalar(
        select(AdminElevation).where(AdminElevation.session_id == actor.session_id)
    )
    active = bool(
        row is not None
        and row.revoked_at is None
        and row.idle_expires_at > now
    )
    return BrowserAdminState(
        elevated=active,
        elevation_expires_at=row.idle_expires_at if active and row is not None else None,
    )


def enter_browser_admin_center(
    session: Session,
    *,
    actor,
    pin: str,
    now: datetime,
    audit_writer: AuditWriter,
    request_id: str,
) -> BrowserAdminState:
    _require_admin(actor)
    result = confirm_admin_pin(
        session,
        actor=actor,
        pin=pin,
        purpose="admin_center",
        now=now,
        audit_writer=audit_writer,
        request_id=request_id,
    )
    return BrowserAdminState(
        elevated=True,
        elevation_expires_at=result.elevation_expires_at,
    )


def require_browser_admin_elevation(
    session: Session,
    *,
    actor,
    now: datetime,
) -> BrowserAdminState:
    _require_admin(actor)
    try:
        expires_at = touch_admin_elevation(session, actor, now)
    except AdminElevationRequired:
        raise AdminElevationRequired(
            "Administrator PIN confirmation is required."
        ) from None
    return BrowserAdminState(elevated=True, elevation_expires_at=expires_at)


def issue_browser_admin_step_up(
    session: Session,
    *,
    actor,
    pin: str,
    purpose: str,
    now: datetime,
    audit_writer: AuditWriter,
    request_id: str,
) -> BrowserAdminStepUp:
    _require_admin(actor)
    if purpose not in STEP_UP_PURPOSES:
        raise ValueError("admin step-up purpose is invalid")
    result = confirm_admin_pin(
        session,
        actor=actor,
        pin=pin,
        purpose=purpose,
        now=now,
        audit_writer=audit_writer,
        request_id=request_id,
    )
    if not result.step_up_token or result.step_up_expires_at is None:
        raise BrowserAdminStepUpRequired(
            "Administrator PIN confirmation is required."
        )
    return BrowserAdminStepUp(
        raw_token=result.step_up_token,
        expires_at=result.step_up_expires_at,
        purpose=purpose,
    )


def consume_browser_admin_step_up(
    session: Session,
    *,
    actor,
    raw_token: str,
    purpose: str,
    now: datetime,
) -> None:
    _require_admin(actor)
    if purpose not in STEP_UP_PURPOSES:
        raise ValueError("admin step-up purpose is invalid")
    try:
        consume_step_up(
            session,
            actor=actor,
            raw_token=raw_token,
            purpose=purpose,
            now=now,
        )
    except StepUpRequired:
        raise BrowserAdminStepUpRequired(
            "Administrator PIN confirmation is required."
        ) from None
