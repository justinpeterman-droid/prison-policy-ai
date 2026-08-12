from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, contains_eager

from backend.identity.audit import AuditEventInput, AuditWriter
from backend.identity.errors import InitialAdminBootstrapRefused, InvalidCredentials
from backend.identity.normalization import normalize_employee_number
from backend.identity.pins import generate_temporary_pin, hash_pin, needs_rehash, normalize_pin, verify_pin
from backend.persistence.models.identity import Account, StaffMember


GENERIC_CREDENTIAL_MESSAGE = "The employee number or PIN is invalid."
BOOTSTRAP_ADVISORY_LOCK_KEY = 6002266223756136276
_DUMMY_PIN_HASH = hash_pin("F9K7Q2")


@dataclass(frozen=True)
class TemporaryPinResult:
    account_id: UUID
    temporary_pin: str
    expires_at: datetime


def lock_minutes(lock_cycle: int) -> int:
    return min(15 * (2 ** max(lock_cycle - 1, 0)), 24 * 60)


def reset_failed_attempts(account: Account) -> None:
    account.failed_attempts = 0
    account.lock_cycle = 0
    account.locked_until = None
    if account.status == "locked":
        account.status = "active"


def unlock_account(account: Account) -> None:
    reset_failed_attempts(account)


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
    locked_staff = session.scalar(
        select(StaffMember).where(StaffMember.id == staff_member.id).with_for_update()
    )
    if locked_staff is None or not locked_staff.is_active:
        raise ValueError("active staff member is required")
    existing = session.scalar(
        select(Account).where(Account.staff_member_id == locked_staff.id).with_for_update()
    )
    if existing is not None:
        raise ValueError("staff member already has an account")
    account, pending_result = _new_account(locked_staff, role, now)
    session.add(account)
    session.flush()
    audit_writer.append(session, AuditEventInput(
        actor_account_id=actor_account_id,
        actor_staff_member_id=actor_staff_member_id,
        action="admin.account_created",
        result="success",
        request_id=request_id,
        target_type="account",
        target_id=account.id,
        details={"target_account_id": str(account.id), "role": role},
    ))
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
    session.execute(text("SELECT pg_advisory_xact_lock(:lock_key)"),
                    {"lock_key": BOOTSTRAP_ADVISORY_LOCK_KEY})
    if session.scalar(select(func.count(Account.id))) != 0:
        raise InitialAdminBootstrapRefused("initial Admin bootstrap is closed")
    staff_member = session.scalar(
        select(StaffMember).where(StaffMember.id == staff_member_id).with_for_update()
    )
    if staff_member is None or not staff_member.is_active:
        raise InitialAdminBootstrapRefused("approved active staff member is required")
    account, pending_result = _new_account(staff_member, "admin", now)
    session.add(account)
    session.flush()
    audit_writer.append(session, AuditEventInput(
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
    ))
    return TemporaryPinResult(account.id, pending_result.temporary_pin, pending_result.expires_at)


def _audit_failure(
    session: Session,
    audit_writer: AuditWriter,
    account: Account | None,
    request_id: str,
    reason: str,
) -> None:
    staff = account.staff_member if account is not None else None
    audit_writer.append(session, AuditEventInput(
        actor_account_id=account.id if account is not None else None,
        actor_staff_member_id=staff.id if staff is not None else None,
        action="auth.login_failed",
        result="failed",
        request_id=request_id,
        target_type="account",
        target_id=account.id if account is not None else None,
        details={"reason": reason},
    ))


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
    if (account.must_change_pin and account.temporary_pin_expires_at is not None
            and account.temporary_pin_expires_at <= now):
        _audit_failure(session, audit_writer, account, request_id, "temporary_pin_expired")
        raise InvalidCredentials(GENERIC_CREDENTIAL_MESSAGE)
    if not pin_valid:
        minutes = record_failed_attempt(account, now)
        _audit_failure(session, audit_writer, account, request_id, "invalid_pin")
        if minutes is not None:
            audit_writer.append(session, AuditEventInput(
                account.id, account.staff_member_id, "auth.locked", "failed", request_id,
                "account", account.id, {"lock_minutes": minutes},
            ))
        raise InvalidCredentials(GENERIC_CREDENTIAL_MESSAGE)

    normalized_pin = str(pin).upper()
    reset_failed_attempts(account)
    account.last_login_at = now
    if needs_rehash(account.pin_hash):
        account.pin_hash = hash_pin(normalized_pin)
    return account


__all__ = [
    "InitialAdminBootstrapRefused",
    "InvalidCredentials",
    "TemporaryPinResult",
    "bootstrap_first_admin",
    "create_account",
    "lock_minutes",
    "record_failed_attempt",
    "reset_failed_attempts",
    "unlock_account",
    "verify_login_pin",
]
