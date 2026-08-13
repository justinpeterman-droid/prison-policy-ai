from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from uuid import UUID

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, contains_eager

from backend.identity.audit import AuditEventInput, AuditWriter
from backend.identity.errors import InitialAdminBootstrapRefused, InvalidCredentials
from backend.identity.normalization import normalize_employee_number
from backend.identity.pins import (
    generate_temporary_pin,
    hash_pin,
    needs_rehash,
    normalize_pin,
    verify_pin,
)
from backend.persistence.models.identity import Account, StaffMember
from backend.persistence.models.sessions import AccessSession


GENERIC_CREDENTIAL_MESSAGE = "The employee number or PIN is invalid."
BOOTSTRAP_ADVISORY_LOCK_KEY = 6002266223756136276
_DUMMY_PIN_HASH = hash_pin("F9K7Q2")


@dataclass(frozen=True)
class TemporaryPinResult:
    account_id: UUID
    temporary_pin: str
    expires_at: datetime


@dataclass(frozen=True)
class Page:
    items: list
    next_cursor: dict[str, str] | None


class LastActiveAdminError(ValueError):
    code = "last_active_admin"


class DuplicateEmployeeNumberError(ValueError):
    code = "duplicate_employee_number"


class AccountAlreadyExistsError(ValueError):
    code = "account_already_exists"


class AccountConflictError(ValueError):
    code = "account_conflict"


def page_from_rows(rows: list, limit: int) -> Page:
    page_size = min(max(int(limit), 1), 100)
    items = list(rows[:page_size])
    next_cursor = None
    if len(rows) > page_size and items:
        last = items[-1]
        next_cursor = {"created_at": last.created_at.isoformat(), "id": str(last.id)}
    return Page(items, next_cursor)


def list_staff(session: Session, *, cursor: dict | None, limit: int, query: str | None) -> Page:
    page_size = min(max(int(limit), 1), 100)
    statement = select(StaffMember)
    if query:
        escaped = query.strip().replace("%", "\\%").replace("_", "\\_")[:100]
        pattern = f"%{escaped}%"
        statement = statement.where(
            or_(
                StaffMember.employee_number.ilike(pattern, escape="\\"),
                StaffMember.first_name.ilike(pattern, escape="\\"),
                StaffMember.last_name.ilike(pattern, escape="\\"),
            )
        )
    if cursor:
        created_at = datetime.fromisoformat(cursor["created_at"].replace("Z", "+00:00"))
        staff_id = UUID(cursor["id"])
        statement = statement.where(
            or_(
                StaffMember.created_at > created_at,
                and_(StaffMember.created_at == created_at, StaffMember.id > staff_id),
            )
        )
    rows = list(session.scalars(statement.order_by(StaffMember.created_at, StaffMember.id).limit(page_size + 1)))
    return page_from_rows(rows, page_size)


def lock_active_admins(session: Session) -> list[Account]:
    return list(
        session.scalars(
            select(Account)
            .where(Account.role == "admin", Account.status == "active")
            .order_by(Account.id)
            .with_for_update()
        )
    )


def ensure_not_last_active_admin(
    target: Account,
    active_admins: list[Account],
    *,
    role: str,
    status: str,
) -> None:
    removes_target = target.role == "admin" and target.status == "active" and (role != "admin" or status != "active")
    if removes_target and not any(item.id != target.id for item in active_admins):
        raise LastActiveAdminError("cannot remove the last active Admin")


def unlock_admin_account(account: Account) -> None:
    account.status = "active"
    account.failed_attempts = 0
    account.lock_cycle = 0
    account.locked_until = None


def _audit_admin(
    session: Session,
    audit_writer: AuditWriter,
    actor,
    action: str,
    target_type: str,
    target_id: UUID,
    details: dict,
    request_id: str,
) -> None:
    audit_writer.append(
        session,
        AuditEventInput(
            actor.account_id,
            actor.staff_member_id,
            action,
            "success",
            request_id,
            target_type,
            target_id,
            details,
        ),
    )


def create_staff(
    session: Session,
    *,
    actor,
    payload: dict,
    now: datetime,
    audit_writer: AuditWriter,
    request_id: str,
) -> StaffMember:
    required = {"employee_number", "rank", "first_name", "last_name", "shift"}
    if set(payload) != required:
        raise ValueError("staff payload is invalid")
    employee_number = normalize_employee_number(payload["employee_number"])
    if session.scalar(select(StaffMember.id).where(StaffMember.employee_number == employee_number)) is not None:
        raise DuplicateEmployeeNumberError("employee number already exists")
    if any(not isinstance(payload[key], str) for key in required):
        raise ValueError("staff payload is invalid")
    values = {key: payload[key].strip() for key in required - {"employee_number"}}
    if not values["first_name"] or not values["last_name"] or not values["shift"]:
        raise ValueError("staff payload is invalid")
    if (
        len(employee_number) > 64
        or len(values["rank"]) > 64
        or len(values["first_name"]) > 100
        or len(values["last_name"]) > 100
        or len(values["shift"]) > 16
    ):
        raise ValueError("staff payload is invalid")
    staff = StaffMember(
        employee_number=employee_number,
        rank=values["rank"],
        first_name=values["first_name"],
        last_name=values["last_name"],
        shift=values["shift"],
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    try:
        with session.begin_nested():
            session.add(staff)
            session.flush()
    except IntegrityError:
        raise DuplicateEmployeeNumberError("employee number already exists") from None
    _audit_admin(
        session,
        audit_writer,
        actor,
        "admin.staff_created",
        "staff_member",
        staff.id,
        {"target_staff_id": str(staff.id)},
        request_id,
    )
    return staff


def update_staff(
    session: Session,
    *,
    actor,
    staff_id: UUID,
    payload: dict,
    now: datetime,
    audit_writer: AuditWriter,
    request_id: str,
) -> StaffMember:
    allowed = {
        "employee_number",
        "rank",
        "first_name",
        "last_name",
        "shift",
        "is_active",
    }
    if not payload or not set(payload) <= allowed:
        raise ValueError("staff payload is invalid")
    staff = session.scalar(select(StaffMember).where(StaffMember.id == staff_id).with_for_update())
    if staff is None:
        raise LookupError("staff member not found")
    changed = []
    for key, value in payload.items():
        if key == "is_active":
            if not isinstance(value, bool):
                raise ValueError("staff payload is invalid")
        elif not isinstance(value, str):
            raise ValueError("staff payload is invalid")
        normalized = normalize_employee_number(value) if key == "employee_number" else value
        if key == "employee_number" and len(normalized) > 64:
            raise ValueError("staff payload is invalid")
        bounds = {"rank": 64, "first_name": 100, "last_name": 100, "shift": 16}
        if key in bounds and (len(normalized) > bounds[key] or (key != "rank" and not normalized)):
            raise ValueError("staff payload is invalid")
        if getattr(staff, key) != normalized:
            setattr(staff, key, normalized)
            changed.append(key)
    staff.updated_at = now
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError:
        raise DuplicateEmployeeNumberError("employee number already exists") from None
    _audit_admin(
        session,
        audit_writer,
        actor,
        "admin.staff_updated",
        "staff_member",
        staff.id,
        {"target_staff_id": str(staff.id), "changed_fields": sorted(changed)},
        request_id,
    )
    return staff


def create_account_for_staff(
    session: Session,
    *,
    actor,
    staff_id: UUID,
    role: str,
    now: datetime,
    audit_writer: AuditWriter,
    request_id: str,
) -> TemporaryPinResult:
    staff = session.scalar(select(StaffMember).where(StaffMember.id == staff_id).with_for_update())
    if staff is None:
        raise LookupError("staff member not found")
    if session.scalar(select(Account.id).where(Account.staff_member_id == staff_id)) is not None:
        raise AccountAlreadyExistsError("staff member already has an account")
    try:
        with session.begin_nested():
            return create_account(
                session,
                staff,
                role,
                now,
                audit_writer,
                request_id,
                actor.account_id,
                actor.staff_member_id,
            )
    except IntegrityError:
        raise AccountAlreadyExistsError("staff member already has an account") from None


def _revoke_account_sessions(session: Session, account_id: UUID, now: datetime) -> list[UUID]:
    rows = list(
        session.scalars(
            select(AccessSession)
            .where(
                AccessSession.account_id == account_id,
                AccessSession.revoked_at.is_(None),
            )
            .order_by(AccessSession.id)
            .with_for_update(nowait=True)
        )
    )
    for row in rows:
        row.revoked_at = now
        row.revoke_reason = "admin_action"
    return [row.id for row in rows]


def change_account_role_or_status(
    session: Session,
    *,
    actor,
    target_account_id: UUID,
    role: str,
    status: str,
    now: datetime,
    audit_writer: AuditWriter,
    request_id: str,
) -> Account:
    if role not in {"user", "admin"} or status not in {"active", "deactivated"}:
        raise ValueError("account role or status is invalid")
    active_admins = lock_active_admins(session)
    target = next((item for item in active_admins if item.id == target_account_id), None)
    if target is None:
        target = session.scalar(select(Account).where(Account.id == target_account_id).with_for_update())
    if target is None:
        raise LookupError("account not found")
    if target.role == "admin" and target.status == "active" and (role != "admin" or status != "active"):
        ensure_not_last_active_admin(target, active_admins, role=role, status=status)
    old_role, old_status = target.role, target.status
    if old_status == "locked" and status == "active":
        raise AccountConflictError("locked accounts must use the unlock operation")
    if (old_role, old_status) == (role, status):
        raise AccountConflictError("the account is already in the requested state")
    target.role = role
    target.status = status
    target.deactivated_at = now if status == "deactivated" else None
    target.updated_at = now
    target.auth_version += 1
    if old_role != role or status == "deactivated":
        _revoke_account_sessions(session, target.id, now)
    session.flush()
    if old_role != role:
        action = "admin.account_role_changed"
        details = {
            "target_account_id": str(target.id),
            "old_role": old_role,
            "new_role": role,
        }
    elif status == "deactivated":
        action = "admin.account_deactivated"
        details = {"target_account_id": str(target.id)}
    else:
        action = "admin.account_reactivated"
        details = {"target_account_id": str(target.id)}
    _audit_admin(session, audit_writer, actor, action, "account", target.id, details, request_id)
    return target


def reset_account_pin(
    session: Session,
    *,
    actor,
    target_account_id: UUID,
    now: datetime,
    audit_writer: AuditWriter,
    request_id: str,
) -> TemporaryPinResult:
    account = session.scalar(select(Account).where(Account.id == target_account_id).with_for_update())
    if account is None:
        raise LookupError("account not found")
    staff = session.scalar(select(StaffMember).where(StaffMember.id == account.staff_member_id))
    if staff is None:
        raise LookupError("account not found")
    temporary_pin = generate_temporary_pin(staff.employee_number)
    account.pin_hash = hash_pin(temporary_pin)
    account.must_change_pin = True
    account.temporary_pin_expires_at = now + timedelta(hours=24)
    account.updated_at = now
    account.auth_version += 1
    reset_failed_attempts(account)
    _revoke_account_sessions(session, account.id, now)
    session.flush()
    _audit_admin(
        session,
        audit_writer,
        actor,
        "auth.pin_reset",
        "account",
        account.id,
        {"target_account_id": str(account.id)},
        request_id,
    )
    return TemporaryPinResult(account.id, temporary_pin, account.temporary_pin_expires_at)


def unlock_account(
    session_or_account,
    *,
    actor=None,
    target_account_id: UUID | None = None,
    now: datetime | None = None,
    audit_writer: AuditWriter | None = None,
    request_id: str | None = None,
) -> Account | None:
    if actor is None:
        reset_failed_attempts(session_or_account)
        return None
    if target_account_id is None or now is None or audit_writer is None or request_id is None:
        raise ValueError("unlock account context is invalid")
    session = session_or_account
    account = session.scalar(select(Account).where(Account.id == target_account_id).with_for_update())
    if account is None:
        raise LookupError("account not found")
    if account.status != "locked":
        raise AccountConflictError("only a locked account can be unlocked")
    account.auth_version += 1
    account.updated_at = now
    _revoke_account_sessions(session, account.id, now)
    unlock_admin_account(account)
    session.flush()
    _audit_admin(
        session,
        audit_writer,
        actor,
        "admin.account_unlocked",
        "account",
        account.id,
        {"target_account_id": str(account.id)},
        request_id,
    )
    return account


def list_accounts(session: Session, *, cursor: dict | None, limit: int) -> Page:
    page_size = min(max(int(limit), 1), 100)
    statement = select(Account)
    if cursor:
        created_at = datetime.fromisoformat(cursor["created_at"].replace("Z", "+00:00"))
        account_id = UUID(cursor["id"])
        statement = statement.where(
            or_(
                Account.created_at > created_at,
                and_(Account.created_at == created_at, Account.id > account_id),
            )
        )
    rows = list(session.scalars(statement.order_by(Account.created_at, Account.id).limit(page_size + 1)))
    return page_from_rows(rows, page_size)


def list_account_sessions(
    session: Session,
    *,
    account_id: UUID,
    cursor: dict | None,
    limit: int,
) -> Page:
    page_size = min(max(int(limit), 1), 100)
    statement = select(AccessSession).where(AccessSession.account_id == account_id)
    if cursor:
        created_at = datetime.fromisoformat(cursor["created_at"].replace("Z", "+00:00"))
        session_id = UUID(cursor["id"])
        statement = statement.where(
            or_(
                AccessSession.created_at > created_at,
                and_(
                    AccessSession.created_at == created_at,
                    AccessSession.id > session_id,
                ),
            )
        )
    rows = list(session.scalars(statement.order_by(AccessSession.created_at, AccessSession.id).limit(page_size + 1)))
    return page_from_rows(rows, page_size)


def revoke_account_sessions(
    session: Session,
    *,
    actor,
    target_account_id: UUID,
    scope: str,
    target_session_id: UUID | None,
    now: datetime,
    audit_writer: AuditWriter,
    request_id: str,
) -> list[UUID]:
    account = session.scalar(select(Account).where(Account.id == target_account_id).with_for_update())
    if account is None:
        raise LookupError("account not found")
    if scope == "one" and target_session_id is not None:
        target_session = session.scalar(
            select(AccessSession).where(AccessSession.id == target_session_id).with_for_update(nowait=True)
        )
        if target_session is None or target_session.account_id != target_account_id:
            raise LookupError("session not found")
        if target_session.revoked_at is not None:
            raise AccountConflictError("the session state changed; reload and try again")
        rows = [target_session]
    elif scope != "all" or target_session_id is not None:
        raise ValueError("session revocation scope is invalid")
    else:
        rows = list(
            session.scalars(
                select(AccessSession)
                .where(
                    AccessSession.account_id == target_account_id,
                    AccessSession.revoked_at.is_(None),
                )
                .order_by(AccessSession.id)
                .with_for_update(nowait=True)
            )
        )
    for row in rows:
        row.revoked_at = now
        row.revoke_reason = "admin_action"
        _audit_admin(
            session,
            audit_writer,
            actor,
            "auth.session_revoked",
            "session",
            row.id,
            {"reason": "admin_action"},
            request_id,
        )
    if scope == "all":
        account.auth_version += 1
        _audit_admin(
            session,
            audit_writer,
            actor,
            "auth.logout_all",
            "account",
            account.id,
            {"session_count": len(rows)},
            request_id,
        )
    session.flush()
    return [row.id for row in rows]


def lock_minutes(lock_cycle: int) -> int:
    return min(15 * (2 ** max(lock_cycle - 1, 0)), 24 * 60)


def reset_failed_attempts(account: Account) -> None:
    account.failed_attempts = 0
    account.lock_cycle = 0
    account.locked_until = None
    if account.status == "locked":
        account.status = "active"


def record_failed_attempt(account: Account, now: datetime) -> int | None:
    account.failed_attempts += 1
    if account.failed_attempts < 5:
        return None
    account.lock_cycle += 1
    minutes = lock_minutes(account.lock_cycle)
    account.status = "locked"
    account.locked_until = now + timedelta(minutes=minutes)
    return minutes


def _new_account(staff_member: StaffMember, role: str, now: datetime) -> tuple[Account, TemporaryPinResult]:
    if role not in {"user", "admin"}:
        raise ValueError("account role is invalid")
    temporary_pin = generate_temporary_pin(staff_member.employee_number)
    expires_at = now + timedelta(hours=24)
    account = Account(
        staff_member_id=staff_member.id,
        role=role,
        status="active",
        pin_hash=hash_pin(temporary_pin),
        must_change_pin=True,
        temporary_pin_expires_at=expires_at,
        failed_attempts=0,
        lock_cycle=0,
        auth_version=1,
    )
    return account, TemporaryPinResult(account.id, temporary_pin, expires_at)


def create_account(
    session: Session,
    staff_member: StaffMember,
    role: str,
    now: datetime,
    audit_writer: AuditWriter,
    request_id: str,
    actor_account_id: UUID,
    actor_staff_member_id: UUID,
) -> TemporaryPinResult:
    if not isinstance(actor_account_id, UUID) or not isinstance(actor_staff_member_id, UUID):
        raise ValueError("authenticated account and staff actors are required")
    locked_staff = session.scalar(select(StaffMember).where(StaffMember.id == staff_member.id).with_for_update())
    if locked_staff is None or not locked_staff.is_active:
        raise ValueError("active staff member is required")
    existing = session.scalar(select(Account).where(Account.staff_member_id == locked_staff.id).with_for_update())
    if existing is not None:
        raise ValueError("staff member already has an account")
    account, pending_result = _new_account(locked_staff, role, now)
    session.add(account)
    session.flush()
    audit_writer.append(
        session,
        AuditEventInput(
            actor_account_id=actor_account_id,
            actor_staff_member_id=actor_staff_member_id,
            action="admin.account_created",
            result="success",
            request_id=request_id,
            target_type="account",
            target_id=account.id,
            details={"target_account_id": str(account.id), "role": role},
        ),
    )
    return TemporaryPinResult(account.id, pending_result.temporary_pin, pending_result.expires_at)


def bootstrap_first_admin(
    session: Session,
    *,
    staff_member_id: UUID,
    now: datetime,
    audit_writer: AuditWriter,
    operation_id: UUID,
    approval_reference_sha256: str,
) -> TemporaryPinResult:
    if not isinstance(operation_id, UUID):
        raise ValueError("operation ID must be a UUID")
    if not isinstance(staff_member_id, UUID):
        raise ValueError("staff member ID must be a UUID")
    if not re.fullmatch(r"[0-9a-f]{64}", approval_reference_sha256):
        raise ValueError("approval reference SHA-256 must be lowercase 64-hex")
    session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": BOOTSTRAP_ADVISORY_LOCK_KEY},
    )
    if session.scalar(select(func.count(Account.id))) != 0:
        raise InitialAdminBootstrapRefused("initial Admin bootstrap is closed")
    staff_member = session.scalar(select(StaffMember).where(StaffMember.id == staff_member_id).with_for_update())
    if staff_member is None or not staff_member.is_active:
        raise InitialAdminBootstrapRefused("approved active staff member is required")
    account, pending_result = _new_account(staff_member, "admin", now)
    session.add(account)
    session.flush()
    audit_writer.append(
        session,
        AuditEventInput(
            actor_account_id=None,
            actor_staff_member_id=None,
            action="system.initial_admin_bootstrapped",
            result="success",
            request_id=str(operation_id),
            target_type="account",
            target_id=account.id,
            details={
                "operation_id": str(operation_id),
                "approval_reference_sha256": approval_reference_sha256,
            },
        ),
    )
    return TemporaryPinResult(account.id, pending_result.temporary_pin, pending_result.expires_at)


def _audit_failure(
    session: Session,
    audit_writer: AuditWriter,
    account: Account | None,
    request_id: str,
    reason: str,
) -> None:
    staff = account.staff_member if account is not None else None
    audit_writer.append(
        session,
        AuditEventInput(
            actor_account_id=account.id if account is not None else None,
            actor_staff_member_id=staff.id if staff is not None else None,
            action="auth.login_failed",
            result="failed",
            request_id=request_id,
            target_type="account",
            target_id=account.id if account is not None else None,
            details={"reason": reason},
        ),
    )


def _dummy_verify(pin: str) -> None:
    try:
        candidate = normalize_pin(pin)
    except Exception:
        candidate = "F9K7Q2"
    verify_pin(_DUMMY_PIN_HASH, candidate)


def _login_account_statement(employee_number: str):
    return (
        select(Account)
        .join(StaffMember, Account.staff_member_id == StaffMember.id)
        .options(contains_eager(Account.staff_member))
        .where(StaffMember.employee_number == employee_number)
        .with_for_update(of=(Account, StaffMember))
    )


def verify_login_pin(
    session: Session,
    *,
    employee_number: str,
    pin: str,
    now: datetime,
    audit_writer: AuditWriter,
    request_id: str,
) -> Account:
    try:
        normalized_employee_number = normalize_employee_number(employee_number)
    except ValueError:
        normalized_employee_number = ""
    account = session.scalar(_login_account_statement(normalized_employee_number))
    if account is None:
        _dummy_verify(pin)
        _audit_failure(session, audit_writer, None, request_id, "invalid_credentials")
        raise InvalidCredentials(GENERIC_CREDENTIAL_MESSAGE)

    pin_valid = verify_pin(account.pin_hash, pin)
    if account.status == "locked" and account.locked_until is not None and account.locked_until <= now:
        account.status = "active"
        account.failed_attempts = 0
        account.locked_until = None
    if account.status != "active":
        _audit_failure(session, audit_writer, account, request_id, "account_locked_or_deactivated")
        raise InvalidCredentials(GENERIC_CREDENTIAL_MESSAGE)
    if not account.staff_member.is_active:
        _audit_failure(session, audit_writer, account, request_id, "staff_inactive")
        raise InvalidCredentials(GENERIC_CREDENTIAL_MESSAGE)
    if (
        account.must_change_pin
        and account.temporary_pin_expires_at is not None
        and account.temporary_pin_expires_at <= now
    ):
        _audit_failure(session, audit_writer, account, request_id, "temporary_pin_expired")
        raise InvalidCredentials(GENERIC_CREDENTIAL_MESSAGE)
    if not pin_valid:
        minutes = record_failed_attempt(account, now)
        _audit_failure(session, audit_writer, account, request_id, "invalid_pin")
        if minutes is not None:
            audit_writer.append(
                session,
                AuditEventInput(
                    account.id,
                    account.staff_member_id,
                    "auth.locked",
                    "failed",
                    request_id,
                    "account",
                    account.id,
                    {"lock_minutes": minutes},
                ),
            )
        raise InvalidCredentials(GENERIC_CREDENTIAL_MESSAGE)

    normalized_pin = str(pin).upper()
    reset_failed_attempts(account)
    account.last_login_at = now
    if needs_rehash(account.pin_hash):
        account.pin_hash = hash_pin(normalized_pin)
    return account


__all__ = [
    "AccountAlreadyExistsError",
    "AccountConflictError",
    "DuplicateEmployeeNumberError",
    "InitialAdminBootstrapRefused",
    "InvalidCredentials",
    "LastActiveAdminError",
    "Page",
    "TemporaryPinResult",
    "bootstrap_first_admin",
    "create_account",
    "create_account_for_staff",
    "create_staff",
    "change_account_role_or_status",
    "list_account_sessions",
    "list_accounts",
    "list_staff",
    "lock_minutes",
    "record_failed_attempt",
    "reset_failed_attempts",
    "reset_account_pin",
    "revoke_account_sessions",
    "unlock_account",
    "update_staff",
    "verify_login_pin",
]
