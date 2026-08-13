from dataclasses import dataclass
from datetime import datetime, timedelta
import hmac
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.identity.accounts import InvalidCredentials, verify_login_pin
from backend.identity.audit import AuditEventInput, AuditWriter
from backend.identity.config import IdentitySettings
from backend.identity.normalization import normalize_device_label
from backend.identity.pins import hash_pin, validate_new_pin, verify_pin
from backend.identity.tokens import hash_device_id, hash_token, issue_credential
from backend.persistence.models.identity import Account, StaffMember
from backend.persistence.models.sessions import AccessSession, RenewalTokenHistory


class SessionReauthenticationRequired(ValueError):
    code = "session_reauthentication_required"

    def __init__(self):
        super().__init__("Sign in again to continue.")


@dataclass(frozen=True)
class SessionTokenPair:
    session_id: UUID
    access_token: str
    renewal_token: str
    access_expires_at: datetime
    renewal_expires_at: datetime
    persistent: bool
    requires_pin_change: bool
    profile: dict[str, str | None]


@dataclass(frozen=True)
class SessionSummary:
    session_id: UUID
    device_label: str
    persistent: bool
    created_at: datetime
    last_used_at: datetime
    renewal_expires_at: datetime
    current: bool


def _profile(account: Account) -> dict[str, str | None]:
    staff = account.staff_member
    display_name = " ".join(part for part in (staff.rank, staff.first_name, staff.last_name) if part)
    return {
        "staff_id": str(staff.id),
        "employee_number": staff.employee_number,
        "display_name": display_name,
        "rank": staff.rank,
        "shift": staff.shift,
        "role": account.role,
        "status": account.status,
    }


def _pair(
    stored: AccessSession,
    account: Account,
    access_token: str,
    renewal_token: str,
) -> SessionTokenPair:
    return SessionTokenPair(
        session_id=stored.id,
        access_token=access_token,
        renewal_token=renewal_token,
        access_expires_at=stored.access_expires_at,
        renewal_expires_at=stored.renewal_expires_at,
        persistent=stored.persistent,
        requires_pin_change=account.must_change_pin,
        profile=_profile(account),
    )


def _require_active(account: Account) -> None:
    if account.status != "active" or not account.staff_member.is_active:
        raise SessionReauthenticationRequired()


def create_session(
    session: Session,
    account: Account,
    *,
    device_id: str,
    device_label: str,
    persistent: bool,
    now: datetime,
    settings: IdentitySettings,
    audit_writer: AuditWriter | None = None,
    request_id: str | None = None,
) -> SessionTokenPair:
    del audit_writer, request_id
    _require_active(account)
    access = issue_credential()
    renewal = issue_credential()
    renewal_seconds = (
        settings.persistent_renewal_ttl_seconds if persistent else settings.nonpersistent_renewal_ttl_seconds
    )
    stored = AccessSession(
        account_id=account.id,
        auth_version=account.auth_version,
        access_token_hash=access.digest,
        access_expires_at=now + timedelta(seconds=settings.access_ttl_seconds),
        renewal_token_hash=renewal.digest,
        renewal_expires_at=now + timedelta(seconds=renewal_seconds),
        renewal_family_id=uuid4(),
        device_id_hash=hash_device_id(device_id, settings.identity_hash_pepper or ""),
        device_label=normalize_device_label(device_label),
        persistent=bool(persistent),
        last_used_at=now,
        created_at=now,
    )
    session.add(stored)
    session.flush()
    return _pair(stored, account, access.raw, renewal.raw)


def login(
    session: Session,
    *,
    employee_number: str,
    pin: str,
    device_id: str,
    device_label: str,
    persistent: bool,
    now: datetime,
    settings: IdentitySettings,
    audit_writer: AuditWriter,
    request_id: str,
) -> SessionTokenPair:
    account = verify_login_pin(
        session,
        employee_number=employee_number,
        pin=pin,
        now=now,
        audit_writer=audit_writer,
        request_id=request_id,
    )
    pair = create_session(
        session,
        account,
        device_id=device_id,
        device_label=device_label,
        persistent=persistent,
        now=now,
        settings=settings,
    )
    audit_writer.append(
        session,
        AuditEventInput(
            account.id,
            account.staff_member_id,
            "auth.login_succeeded",
            "success",
            request_id,
            "session",
            pair.session_id,
            {"persistent": bool(persistent)},
        ),
    )
    return pair


def _account_for_session(session: Session, stored: AccessSession, *, lock: bool = False) -> Account | None:
    statement = (
        select(Account)
        .join(StaffMember, Account.staff_member_id == StaffMember.id)
        .where(Account.id == stored.account_id)
    )
    if lock:
        statement = statement.with_for_update(of=(Account, StaffMember))
    account = session.scalar(statement)
    if account is not None and "staff_member" not in account.__dict__:
        account.staff_member = session.scalar(select(StaffMember).where(StaffMember.id == account.staff_member_id))
    return account


def _revoke_family(
    session: Session,
    current: AccessSession,
    *,
    now: datetime,
    reason: str,
) -> int:
    rows = list(
        session.scalars(
            select(AccessSession)
            .where(AccessSession.renewal_family_id == current.renewal_family_id)
            .order_by(AccessSession.id)
            .with_for_update()
        ).all()
    )
    if current not in rows:
        rows.append(current)
    count = 0
    for row in rows:
        if row.revoked_at is None:
            row.revoked_at = now
            row.revoke_reason = reason
            count += 1
    return count


def renew_session(
    session: Session,
    *,
    supplied_renewal_token: str,
    device_id: str,
    now: datetime,
    settings: IdentitySettings,
    audit_writer: AuditWriter,
    request_id: str,
) -> SessionTokenPair:
    supplied_hash = hash_token(supplied_renewal_token)
    current = session.scalar(
        select(AccessSession).where(AccessSession.renewal_token_hash == supplied_hash).with_for_update()
    )
    if current is None:
        history = session.scalar(
            select(RenewalTokenHistory).where(RenewalTokenHistory.token_hash == supplied_hash).with_for_update()
        )
        if history is None:
            raise SessionReauthenticationRequired()
        current = session.scalar(select(AccessSession).where(AccessSession.id == history.session_id).with_for_update())
        if current is None:
            raise SessionReauthenticationRequired()
        account = _account_for_session(session, current)
        history.reuse_detected_at = history.reuse_detected_at or now
        _revoke_family(session, current, now=now, reason="renewal_reuse")
        if account is not None:
            audit_writer.append(
                session,
                AuditEventInput(
                    account.id,
                    account.staff_member_id,
                    "auth.session_revoked",
                    "failed",
                    request_id,
                    "session",
                    current.id,
                    {"reason": "renewal_reuse"},
                ),
            )
        session.flush()
        raise SessionReauthenticationRequired()

    account = _account_for_session(session, current, lock=True)
    if account is None:
        raise SessionReauthenticationRequired()
    expected_device_hash = hash_device_id(device_id, settings.identity_hash_pepper or "")
    if (
        current.revoked_at is not None
        or current.renewal_expires_at <= now
        or not hmac.compare_digest(current.device_id_hash, expected_device_hash)
        or current.auth_version != account.auth_version
    ):
        raise SessionReauthenticationRequired()
    _require_active(account)

    old_expiry = current.renewal_expires_at
    session.add(
        RenewalTokenHistory(
            session_id=current.id,
            renewal_family_id=current.renewal_family_id,
            token_hash=current.renewal_token_hash,
            rotated_at=now,
            expires_at=old_expiry,
        )
    )
    access = issue_credential()
    renewal = issue_credential()
    current.access_token_hash = access.digest
    current.renewal_token_hash = renewal.digest
    current.access_expires_at = now + timedelta(seconds=settings.access_ttl_seconds)
    current.last_used_at = now
    if current.persistent:
        current.renewal_expires_at = now + timedelta(seconds=settings.persistent_renewal_ttl_seconds)
    audit_writer.append(
        session,
        AuditEventInput(
            account.id,
            account.staff_member_id,
            "auth.session_renewed",
            "success",
            request_id,
            "session",
            current.id,
            {"persistent": current.persistent},
        ),
    )
    session.flush()
    return _pair(current, account, access.raw, renewal.raw)


def resolve_access_session(
    session: Session,
    *,
    access_token: str,
    now: datetime,
) -> tuple[AccessSession, Account]:
    stored = session.scalar(select(AccessSession).where(AccessSession.access_token_hash == hash_token(access_token)))
    if stored is None:
        raise SessionReauthenticationRequired()
    account = _account_for_session(session, stored)
    if (
        account is None
        or stored.revoked_at is not None
        or stored.access_expires_at <= now
        or stored.auth_version != account.auth_version
    ):
        raise SessionReauthenticationRequired()
    _require_active(account)
    return stored, account


def revoke_session(
    session: Session,
    *,
    actor_account_id: UUID,
    target_session_id: UUID,
    now: datetime,
    audit_writer: AuditWriter,
    request_id: str,
) -> int:
    target = session.scalar(select(AccessSession).where(AccessSession.id == target_session_id).with_for_update())
    if target is None or target.account_id != actor_account_id:
        raise SessionReauthenticationRequired()
    account = _account_for_session(session, target)
    if account is None:
        raise SessionReauthenticationRequired()
    count = _revoke_family(session, target, now=now, reason="user_revoked")
    audit_writer.append(
        session,
        AuditEventInput(
            actor_account_id,
            account.staff_member_id,
            "auth.session_revoked",
            "success",
            request_id,
            "session",
            target.id,
            {"reason": "user_revoked"},
        ),
    )
    return count


def logout_all(
    session: Session,
    *,
    account_id: UUID,
    now: datetime,
    audit_writer: AuditWriter,
    request_id: str,
) -> int:
    rows = list(
        session.scalars(
            select(AccessSession)
            .where(AccessSession.account_id == account_id)
            .order_by(AccessSession.id)
            .with_for_update()
        ).all()
    )
    account = session.scalar(select(Account).where(Account.id == account_id).with_for_update())
    if account is None:
        raise SessionReauthenticationRequired()
    account.auth_version += 1
    count = 0
    for row in rows:
        if row.revoked_at is None:
            row.revoked_at = now
            row.revoke_reason = "logout_all"
            count += 1
    audit_writer.append(
        session,
        AuditEventInput(
            account.id,
            account.staff_member_id,
            "auth.logout_all",
            "success",
            request_id,
            "account",
            account.id,
            {"session_count": count},
        ),
    )
    return count


def change_pin(
    session: Session,
    *,
    account_id: UUID,
    current_session_id: UUID,
    current_pin: str,
    new_pin: str,
    device_id: str,
    now: datetime,
    settings: IdentitySettings,
    audit_writer: AuditWriter,
    request_id: str,
) -> SessionTokenPair:
    current = session.scalar(
        select(AccessSession)
        .where(
            AccessSession.id == current_session_id,
            AccessSession.account_id == account_id,
        )
        .with_for_update()
    )
    account = session.scalar(select(Account).where(Account.id == account_id).with_for_update())
    if account is None or current is None:
        raise SessionReauthenticationRequired()
    if "staff_member" not in account.__dict__:
        account.staff_member = session.scalar(select(StaffMember).where(StaffMember.id == account.staff_member_id))
    expected_device = hash_device_id(device_id, settings.identity_hash_pepper or "")
    if (
        current.revoked_at is not None
        or current.renewal_expires_at <= now
        or current.auth_version != account.auth_version
        or not hmac.compare_digest(current.device_id_hash, expected_device)
    ):
        raise SessionReauthenticationRequired()
    _require_active(account)
    if not verify_pin(account.pin_hash, current_pin):
        raise InvalidCredentials()
    normalized_new_pin = validate_new_pin(new_pin, account.staff_member.employee_number)

    account.pin_hash = hash_pin(normalized_new_pin)
    account.must_change_pin = False
    account.temporary_pin_expires_at = None
    account.auth_version += 1
    rows = list(
        session.scalars(
            select(AccessSession)
            .where(AccessSession.account_id == account_id)
            .order_by(AccessSession.id)
            .with_for_update()
        ).all()
    )
    for row in rows:
        if row.id != current.id and row.revoked_at is None:
            row.revoked_at = now
            row.revoke_reason = "pin_changed"

    session.add(
        RenewalTokenHistory(
            session_id=current.id,
            renewal_family_id=current.renewal_family_id,
            token_hash=current.renewal_token_hash,
            rotated_at=now,
            expires_at=current.renewal_expires_at,
        )
    )
    access = issue_credential()
    renewal = issue_credential()
    current.auth_version = account.auth_version
    current.access_token_hash = access.digest
    current.renewal_token_hash = renewal.digest
    current.access_expires_at = now + timedelta(seconds=settings.access_ttl_seconds)
    current.last_used_at = now
    if current.persistent:
        current.renewal_expires_at = now + timedelta(seconds=settings.persistent_renewal_ttl_seconds)
    audit_writer.append(
        session,
        AuditEventInput(
            account.id,
            account.staff_member_id,
            "auth.pin_changed",
            "success",
            request_id,
            "account",
            account.id,
            {},
        ),
    )
    session.flush()
    return _pair(current, account, access.raw, renewal.raw)


def list_sessions(
    session: Session,
    *,
    account_id: UUID,
    current_session_id: UUID,
) -> list[SessionSummary]:
    rows = list(
        session.scalars(
            select(AccessSession)
            .where(AccessSession.account_id == account_id)
            .order_by(AccessSession.created_at.desc(), AccessSession.id)
        ).all()
    )
    return [
        SessionSummary(
            session_id=row.id,
            device_label=row.device_label,
            persistent=row.persistent,
            created_at=row.created_at,
            last_used_at=row.last_used_at,
            renewal_expires_at=row.renewal_expires_at,
            current=row.id == current_session_id,
        )
        for row in rows
        if row.revoked_at is None
    ]
