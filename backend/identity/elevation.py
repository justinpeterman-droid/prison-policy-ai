from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.identity.audit import AuditEventInput, AuditWriter
from backend.identity.pins import verify_pin
from backend.identity.tokens import hash_token, issue_credential
from backend.persistence.models.identity import Account, StaffMember
from backend.persistence.models.sessions import (
    AccessSession,
    AdminElevation,
    AdminStepUpToken,
)


STEP_UP_PURPOSES = {
    "staff_write",
    "account_create",
    "account_role_status",
    "account_reset_pin",
    "account_unlock",
    "account_revoke_sessions",
    "report_restore",
    "report_transfer",
    "bulk_export",
    "audit_export",
    "review_lab_handoff",
}
ALL_ADMIN_CONFIRMATION_PURPOSES = {"admin_center"} | STEP_UP_PURPOSES


class AdminElevationRequired(PermissionError):
    code = "admin_elevation_required"


class StepUpRequired(PermissionError):
    code = "step_up_required"


@dataclass(frozen=True)
class ElevationResult:
    elevation_expires_at: datetime
    step_up_token: str | None
    step_up_expires_at: datetime | None
    purpose: str


def elevation_deadline(now: datetime) -> datetime:
    return now + timedelta(minutes=15)


def step_up_deadline(now: datetime) -> datetime:
    return now + timedelta(minutes=5)


def _elevation(session: Session, actor):
    return session.scalar(
        select(AdminElevation)
        .where(AdminElevation.session_id == actor.session_id)
        .with_for_update()
    )


def elevation_is_active(session: Session, actor, now: datetime) -> bool:
    row = _elevation(session, actor)
    return bool(row and row.revoked_at is None and row.idle_expires_at > now)


def touch_admin_elevation(session: Session, actor, now: datetime) -> datetime:
    row = _elevation(session, actor)
    if row is None or row.revoked_at is not None or row.idle_expires_at <= now:
        raise AdminElevationRequired("Administrator PIN confirmation is required.")
    row.last_used_at = now
    row.idle_expires_at = elevation_deadline(now)
    session.flush()
    return row.idle_expires_at


def confirm_admin_pin(
    session: Session,
    *,
    actor,
    pin: str,
    purpose: str,
    now: datetime,
    audit_writer: AuditWriter,
    request_id: str,
) -> ElevationResult:
    if purpose not in ALL_ADMIN_CONFIRMATION_PURPOSES:
        raise ValueError("admin confirmation purpose is invalid")
    access_session = session.scalar(
        select(AccessSession)
        .where(AccessSession.id == actor.session_id)
        .with_for_update()
    )
    account = session.scalar(
        select(Account).where(Account.id == actor.account_id).with_for_update()
    )
    staff = session.scalar(
        select(StaffMember)
        .where(StaffMember.id == actor.staff_member_id)
        .with_for_update()
    )
    if (
        account is None
        or access_session is None
        or staff is None
        or actor.role != "admin"
        or account.role != "admin"
        or account.status != "active"
        or account.staff_member_id != actor.staff_member_id
        or not staff.is_active
        or access_session.account_id != actor.account_id
        or access_session.revoked_at is not None
        or access_session.access_expires_at <= now
        or access_session.auth_version != account.auth_version
        or actor.auth_version != account.auth_version
        or not verify_pin(account.pin_hash, pin)
    ):
        audit_writer.append(
            session,
            AuditEventInput(
                actor.account_id,
                actor.staff_member_id,
                "auth.step_up_failed",
                "failed",
                request_id,
                "account",
                actor.account_id,
                {"purpose": purpose, "reason": "invalid_confirmation"},
            ),
        )
        raise StepUpRequired("Administrator PIN confirmation is required.")
    elevation = _elevation(session, actor)
    deadline = elevation_deadline(now)
    if elevation is None:
        elevation = AdminElevation(
            session_id=actor.session_id,
            issued_at=now,
            last_used_at=now,
            idle_expires_at=deadline,
            revoked_at=None,
        )
        session.add(elevation)
    else:
        elevation.issued_at = now
        elevation.last_used_at = now
        elevation.idle_expires_at = deadline
        elevation.revoked_at = None
    raw_token = None
    token_deadline = None
    if purpose in STEP_UP_PURPOSES:
        credential = issue_credential()
        raw_token = credential.raw
        token_deadline = step_up_deadline(now)
        session.add(
            AdminStepUpToken(
                session_id=actor.session_id,
                token_hash=credential.digest,
                purpose=purpose,
                issued_at=now,
                expires_at=token_deadline,
            )
        )
    session.flush()
    audit_writer.append(
        session,
        AuditEventInput(
            actor.account_id,
            actor.staff_member_id,
            "auth.step_up_succeeded",
            "success",
            request_id,
            "account",
            actor.account_id,
            {"purpose": purpose},
        ),
    )
    return ElevationResult(deadline, raw_token, token_deadline, purpose)


def consume_step_up(
    session: Session,
    *,
    actor,
    raw_token: str,
    purpose: str,
    now: datetime,
) -> None:
    try:
        digest = hash_token(raw_token)
    except ValueError:
        raise StepUpRequired("Administrator PIN confirmation is required.") from None
    row = session.scalar(
        select(AdminStepUpToken)
        .where(AdminStepUpToken.token_hash == digest)
        .with_for_update()
    )
    if (
        row is None
        or row.session_id != actor.session_id
        or row.purpose != purpose
        or row.used_at is not None
        or row.revoked_at is not None
        or row.expires_at <= now
    ):
        raise StepUpRequired("Administrator PIN confirmation is required.")
    row.used_at = now
    session.flush()
