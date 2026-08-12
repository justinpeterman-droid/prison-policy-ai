from datetime import UTC, datetime
import re

from flask import Blueprint, current_app, request
from sqlalchemy.exc import SQLAlchemyError

from backend.identity.accounts import InvalidCredentials
from backend.identity.config import IdentitySettings
from backend.identity.sessions import (
    SessionReauthenticationRequired,
    SessionTokenPair,
    login,
    renew_session,
)
from backend.identity.tokens import hash_device_id
from backend.persistence.database import DatabaseUnavailable, session_scope
from backend.webapp.api_v1.context import request_id
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.responses import success


auth_bp = Blueprint("auth_api", __name__)
LOGIN_FIELDS = {"employee_number", "pin", "device_id", "device_label", "persistent"}
RENEW_FIELDS = {"renewal_token", "device_id"}


def _json_object(fields: set[str]) -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != fields:
        raise ApiError("validation_failed", "The request body is invalid.", status=400)
    return payload


def _required_string(payload: dict, field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise ApiError("validation_failed", "The request body is invalid.", status=400)
    return value


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _token_data(pair: SessionTokenPair) -> dict[str, object]:
    return {
        "session_id": str(pair.session_id),
        "access_token": pair.access_token,
        "renewal_token": pair.renewal_token,
        "access_expires_at": _timestamp(pair.access_expires_at),
        "renewal_expires_at": _timestamp(pair.renewal_expires_at),
        "persistent": pair.persistent,
        "requires_pin_change": pair.requires_pin_change,
        "profile": pair.profile,
    }


def _dependencies() -> tuple[IdentitySettings, object]:
    settings: IdentitySettings = current_app.config["IDENTITY_SETTINGS"]
    audit_writer = current_app.config.get("AUDIT_WRITER")
    if audit_writer is None:
        raise ApiError(
            "dependency_unavailable",
            "Authentication is temporarily unavailable.",
            status=503,
            retryable=True,
        )
    return settings, audit_writer


def _validated_device_id(payload: dict, settings: IdentitySettings) -> str:
    value = _required_string(payload, "device_id")
    try:
        hash_device_id(value, settings.identity_hash_pepper or "")
    except ValueError:
        raise ApiError("validation_failed", "The request body is invalid.", status=400) from None
    return value


def _validated_pin(payload: dict) -> str:
    value = _required_string(payload, "pin")
    if not re.fullmatch(r"[A-Za-z0-9]{4,8}", value):
        raise ApiError("validation_failed", "The request body is invalid.", status=400)
    return value


def _validated_renewal_token(payload: dict) -> str:
    value = _required_string(payload, "renewal_token")
    if not 40 <= len(value) <= 512 or not value.isascii() or any(character.isspace() for character in value):
        raise ApiError("validation_failed", "The request body is invalid.", status=400)
    return value


@auth_bp.post("/login", endpoint="login")
def login_route():
    payload = _json_object(LOGIN_FIELDS)
    if not isinstance(payload["persistent"], bool):
        raise ApiError("validation_failed", "The request body is invalid.", status=400)
    settings, audit_writer = _dependencies()
    employee_number = _required_string(payload, "employee_number")
    pin = _validated_pin(payload)
    device_id = _validated_device_id(payload, settings)
    device_label = _required_string(payload, "device_label")
    if len(device_label) > 120:
        raise ApiError("validation_failed", "The request body is invalid.", status=400)
    pending_error: InvalidCredentials | None = None
    pair = None
    try:
        with session_scope() as db_session:
            try:
                pair = login(
                    db_session,
                    employee_number=employee_number,
                    pin=pin,
                    device_id=device_id,
                    device_label=device_label,
                    persistent=payload["persistent"],
                    now=datetime.now(UTC),
                    settings=settings,
                    audit_writer=audit_writer,
                    request_id=request_id(),
                )
            except InvalidCredentials as error:
                pending_error = error
    except (DatabaseUnavailable, SQLAlchemyError):
        raise ApiError(
            "dependency_unavailable",
            "Authentication is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    if pending_error is not None:
        raise ApiError("invalid_credentials", str(pending_error), status=401)
    if pair is None:
        raise ApiError("dependency_unavailable", "Authentication is temporarily unavailable.", status=503, retryable=True)
    return success(_token_data(pair))


@auth_bp.post("/renew", endpoint="renew")
def renew_route():
    payload = _json_object(RENEW_FIELDS)
    settings, audit_writer = _dependencies()
    renewal_token = _validated_renewal_token(payload)
    device_id = _validated_device_id(payload, settings)
    pending_error: SessionReauthenticationRequired | None = None
    pair = None
    try:
        with session_scope() as db_session:
            try:
                pair = renew_session(
                    db_session,
                    supplied_renewal_token=renewal_token,
                    device_id=device_id,
                    now=datetime.now(UTC),
                    settings=settings,
                    audit_writer=audit_writer,
                    request_id=request_id(),
                )
            except SessionReauthenticationRequired as error:
                pending_error = error
    except (DatabaseUnavailable, SQLAlchemyError):
        raise ApiError(
            "dependency_unavailable",
            "Authentication is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    if pending_error is not None:
        raise ApiError(
            "session_reauthentication_required",
            str(pending_error),
            status=401,
        )
    if pair is None:
        raise ApiError("dependency_unavailable", "Authentication is temporarily unavailable.", status=503, retryable=True)
    return success(_token_data(pair))
