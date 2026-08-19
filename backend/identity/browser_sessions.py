"""Cookie-safe browser session adapter over the existing identity service."""
from dataclasses import dataclass
from datetime import datetime
from hmac import compare_digest
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from backend.identity.config import IdentitySettings
from backend.identity.sessions import (
    SessionTokenPair,
    login,
    renew_session,
    resolve_access_session,
)
from backend.identity.tokens import hash_token, issue_credential
from backend.persistence.models import Account
from backend.persistence.models.browser import BrowserSessionBinding
from backend.persistence.models.sessions import AccessSession


class BrowserCsrfInvalid(ValueError):
    """Raised when a browser mutation lacks the session-bound CSRF value."""


class BrowserSessionInvalid(RuntimeError):
    """Raised when an identity session cannot be resolved into browser state."""


@dataclass(frozen=True)
class BrowserActor:
    account_id: UUID
    staff_member_id: UUID
    session_id: UUID
    role: Literal["user", "admin"]
    auth_version: int
    must_change_pin: bool


@dataclass(frozen=True)
class BrowserCookiePair:
    access_token: str
    renewal_token: str
    csrf_token: str
    access_expires_at: datetime
    renewal_expires_at: datetime
    persistent: bool


def _actor(stored: AccessSession, account: Account) -> BrowserActor:
    return BrowserActor(
        account_id=account.id,
        staff_member_id=account.staff_member_id,
        session_id=stored.id,
        role=account.role,
        auth_version=account.auth_version,
        must_change_pin=account.must_change_pin,
    )


def _resolved(db: Session, session_id: UUID) -> tuple[AccessSession, Account]:
    stored = db.get(AccessSession, session_id)
    if stored is None:
        raise BrowserSessionInvalid("Browser session is unavailable.")
    account = db.get(Account, stored.account_id)
    if account is None:
        raise BrowserSessionInvalid("Browser account is unavailable.")
    return stored, account


def _cookies(pair: SessionTokenPair, csrf_token: str) -> BrowserCookiePair:
    return BrowserCookiePair(
        access_token=pair.access_token,
        renewal_token=pair.renewal_token,
        csrf_token=csrf_token,
        access_expires_at=pair.access_expires_at,
        renewal_expires_at=pair.renewal_expires_at,
        persistent=pair.persistent,
    )


def create_browser_session(
    db: Session,
    *,
    employee_number: str,
    pin: str,
    device_id: str,
    device_label: str,
    persistent: bool,
    now: datetime,
    settings: IdentitySettings,
    audit_writer,
    request_id: str,
) -> tuple[BrowserActor, BrowserCookiePair]:
    """Authenticate an employee and bind a random CSRF value to the session."""
    pair = login(
        db,
        employee_number=employee_number,
        pin=pin,
        device_id=device_id,
        device_label=device_label,
        persistent=persistent,
        now=now,
        settings=settings,
        audit_writer=audit_writer,
        request_id=request_id,
    )
    stored, account = _resolved(db, pair.session_id)
    csrf = issue_credential()
    db.add(
        BrowserSessionBinding(
            session_id=pair.session_id,
            csrf_token_hash=csrf.digest,
            created_at=now,
            rotated_at=now,
        )
    )
    return _actor(stored, account), _cookies(pair, csrf.raw)


def resolve_browser_actor(
    db: Session,
    *,
    access_token: str,
    now: datetime,
) -> BrowserActor:
    """Resolve the opaque access cookie through the shared identity service."""
    stored, account = resolve_access_session(db, access_token=access_token, now=now)
    return _actor(stored, account)


def validate_browser_csrf(
    db: Session,
    *,
    actor: BrowserActor,
    supplied_token: str,
) -> None:
    """Validate a readable CSRF token against the digest bound to the session."""
    if not supplied_token:
        raise BrowserCsrfInvalid("CSRF confirmation is required.")
    binding = db.get(BrowserSessionBinding, actor.session_id)
    if binding is None:
        raise BrowserCsrfInvalid("CSRF confirmation is required.")
    try:
        supplied_hash = hash_token(supplied_token)
    except ValueError as error:
        raise BrowserCsrfInvalid("CSRF confirmation is invalid.") from error
    if not compare_digest(binding.csrf_token_hash, supplied_hash):
        raise BrowserCsrfInvalid("CSRF confirmation is invalid.")


def renew_browser_session(
    db: Session,
    *,
    renewal_token: str,
    device_id: str,
    csrf_token: str,
    now: datetime,
    settings: IdentitySettings,
    audit_writer,
    request_id: str,
) -> tuple[BrowserActor, BrowserCookiePair]:
    """Rotate identity credentials and the browser CSRF value atomically."""
    pair = renew_session(
        db,
        supplied_renewal_token=renewal_token,
        device_id=device_id,
        now=now,
        settings=settings,
        audit_writer=audit_writer,
        request_id=request_id,
    )
    stored, account = _resolved(db, pair.session_id)
    actor = _actor(stored, account)
    validate_browser_csrf(db, actor=actor, supplied_token=csrf_token)
    csrf = issue_credential()
    binding = db.get(BrowserSessionBinding, pair.session_id)
    if binding is None:
        raise BrowserSessionInvalid("Browser session binding is unavailable.")
    binding.csrf_token_hash = csrf.digest
    binding.rotated_at = now
    return actor, _cookies(pair, csrf.raw)
