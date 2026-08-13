from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from uuid import UUID, uuid4

from flask import g, jsonify, request
from sqlalchemy import false, select
from sqlalchemy.orm import Session

from backend.identity.audit import AuditEventInput, AuditWriter
from backend.identity.elevation import consume_step_up, touch_admin_elevation
from backend.identity.tokens import hash_token, issue_credential
from backend.persistence.models.identity import Account, StaffMember
from backend.persistence.models.security import BrowserHandoff, BrowserSession
from backend.persistence.models.sessions import AccessSession


class HandoffInvalid(PermissionError):
    code = "handoff_invalid"


class BrowserSessionInvalid(PermissionError):
    code = "browser_session_invalid"


@dataclass(frozen=True)
class BrowserHandoffResult:
    handoff_id: UUID
    token: str
    expires_at: datetime


@dataclass(frozen=True)
class BrowserSessionResult:
    browser_session_id: UUID
    cookie_value: str
    expires_at: datetime


@dataclass(frozen=True)
class BrowserActor:
    account_id: UUID
    staff_member_id: UUID
    browser_session_id: UUID
    role: str


def issue_browser_handoff(
    session: Session,
    *,
    actor,
    now: datetime,
    audit_writer: AuditWriter,
    request_id: str,
    step_up_token: str,
) -> BrowserHandoffResult:
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
        actor.role != "admin"
        or access_session is None
        or account is None
        or staff is None
        or access_session.account_id != actor.account_id
        or access_session.revoked_at is not None
        or access_session.access_expires_at <= now
        or access_session.auth_version != account.auth_version
        or account.id != actor.account_id
        or account.staff_member_id != actor.staff_member_id
        or account.role != "admin"
        or account.status != "active"
        or actor.auth_version != account.auth_version
        or not staff.is_active
    ):
        raise HandoffInvalid("Review Lab handoff is unavailable.")
    touch_admin_elevation(session, actor, now)
    consume_step_up(
        session,
        actor=actor,
        raw_token=step_up_token,
        purpose="review_lab_handoff",
        now=now,
    )
    credential = issue_credential()
    handoff_id = uuid4()
    expires_at = now + timedelta(seconds=60)
    session.add(
        BrowserHandoff(
            id=handoff_id,
            account_id=actor.account_id,
            session_id=actor.session_id,
            token_hash=credential.digest,
            purpose="review_lab",
            expires_at=expires_at,
            created_at=now,
        )
    )
    session.flush()
    audit_writer.append(
        session,
        AuditEventInput(
            actor.account_id,
            actor.staff_member_id,
            "admin.review_lab_handoff_issued",
            "success",
            request_id,
            "browser_handoff",
            handoff_id,
            {"handoff_id": str(handoff_id)},
        ),
    )
    return BrowserHandoffResult(handoff_id, credential.raw, expires_at)


def _invalid_handoff() -> HandoffInvalid:
    return HandoffInvalid("This Review Lab link is invalid or expired.")


def redeem_browser_handoff(
    session: Session,
    *,
    raw_token: str,
    now: datetime,
    audit_writer: AuditWriter,
    request_id: str,
) -> BrowserSessionResult:
    try:
        digest = hash_token(raw_token)
    except ValueError:
        raise _invalid_handoff() from None
    handoff = session.scalar(
        select(BrowserHandoff)
        .where(BrowserHandoff.token_hash == digest)
        .with_for_update()
    )
    if (
        handoff is None
        or handoff.purpose != "review_lab"
        or handoff.revoked_at is not None
        or handoff.redeemed_at is not None
        or handoff.expires_at <= now
    ):
        raise _invalid_handoff()
    access_session = session.scalar(
        select(AccessSession)
        .where(AccessSession.id == handoff.session_id)
        .with_for_update()
    )
    account = session.scalar(
        select(Account).where(Account.id == handoff.account_id).with_for_update()
    )
    staff = session.scalar(
        select(StaffMember)
        .where(StaffMember.id == account.staff_member_id)
        .with_for_update()
        if account is not None
        else select(StaffMember).where(false())
    )
    if (
        access_session is None
        or account is None
        or staff is None
        or access_session.account_id != account.id
        or access_session.revoked_at is not None
        or access_session.renewal_expires_at <= now
        or access_session.auth_version != account.auth_version
        or account.role != "admin"
        or account.status != "active"
        or not staff.is_active
    ):
        raise _invalid_handoff()
    handoff.redeemed_at = now
    credential = issue_credential()
    browser_session_id = uuid4()
    expires_at = now + timedelta(minutes=30)
    session.add(
        BrowserSession(
            id=browser_session_id,
            account_id=account.id,
            issuing_session_id=access_session.id,
            token_hash=credential.digest,
            purpose="review_lab",
            last_used_at=now,
            expires_at=expires_at,
            created_at=now,
        )
    )
    session.flush()
    audit_writer.append(
        session,
        AuditEventInput(
            account.id,
            staff.id,
            "admin.review_lab_handoff_redeemed",
            "success",
            request_id,
            "browser_session",
            browser_session_id,
            {
                "handoff_id": str(handoff.id),
                "browser_session_id": str(browser_session_id),
            },
        ),
    )
    return BrowserSessionResult(browser_session_id, credential.raw, expires_at)


def resolve_browser_session(
    session: Session,
    *,
    cookie_value: str,
    now: datetime,
) -> BrowserActor:
    try:
        digest = hash_token(cookie_value)
    except ValueError:
        raise BrowserSessionInvalid("Review Lab access is unavailable.") from None
    stored = session.scalar(
        select(BrowserSession)
        .where(BrowserSession.token_hash == digest)
        .with_for_update()
    )
    if (
        stored is None
        or stored.purpose != "review_lab"
        or stored.revoked_at is not None
        or stored.expires_at <= now
    ):
        raise BrowserSessionInvalid("Review Lab access is unavailable.")
    account = session.scalar(
        select(Account).where(Account.id == stored.account_id).with_for_update()
    )
    staff = session.scalar(
        select(StaffMember)
        .where(StaffMember.id == account.staff_member_id)
        .with_for_update()
        if account is not None
        else select(StaffMember).where(false())
    )
    if (
        account is None
        or staff is None
        or account.role != "admin"
        or account.status != "active"
        or not staff.is_active
    ):
        raise BrowserSessionInvalid("Review Lab access is unavailable.")
    stored.last_used_at = now
    stored.expires_at = now + timedelta(minutes=30)
    session.flush()
    return BrowserActor(account.id, staff.id, stored.id, account.role)


def require_review_lab_access(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if getattr(g, "browser_actor", None) is not None:
            g.review_lab_access_kind = "individual_browser_session"
            return view(*args, **kwargs)
        if getattr(g, "review_lab_access_kind", None) == "legacy_shared_admin":
            return view(*args, **kwargs)
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found."}), 404
        return "Not found.", 404

    return wrapped
