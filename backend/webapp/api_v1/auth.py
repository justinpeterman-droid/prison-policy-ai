from datetime import UTC, datetime
import ipaddress
import re
from uuid import UUID

from flask import Blueprint, current_app, g, request
from sqlalchemy.exc import SQLAlchemyError

from backend.identity.accounts import InvalidCredentials
from backend.identity.config import IdentitySettings
from backend.identity.sessions import (
    SessionReauthenticationRequired,
    SessionTokenPair,
    login,
    list_sessions,
    logout_all,
    change_pin,
    revoke_session,
    renew_session,
)
from backend.identity.idempotency import (
    IdempotencyConflict,
    RequestInProgress,
    claim_idempotency,
    complete_idempotency,
    request_digest,
)
from backend.identity.rate_limits import consume_limit
from backend.identity.normalization import normalize_employee_number
from backend.identity.tokens import hash_device_id
from backend.identity.elevation import StepUpRequired, confirm_admin_pin
from backend.persistence.database import DatabaseUnavailable, session_scope
from backend.persistence.models.security import IdempotencyRecord
from backend.webapp.api_v1.context import request_id
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.responses import success
from backend.webapp.api_v1.client_policy import require_compatible_write
from backend.webapp.api_v1.middleware import (
    current_actor,
    current_request_session,
    require_access_token,
    require_role,
)


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


def _consume_login_limits(db_session, payload: dict, settings: IdentitySettings) -> None:
    if (
        not current_app.config.get("AUTH_RATE_LIMITS_ENABLED", True)
        or not hasattr(db_session, "execute")
    ):
        return
    pepper = settings.identity_hash_pepper or ""
    try:
        employee = normalize_employee_number(payload["employee_number"])
    except ValueError:
        employee = "invalid"
    candidates = [request.remote_addr or ""]
    if current_app.config.get("TRUST_CLOUD_RUN_PROXY", False):
        candidates = request.headers.get("X-Forwarded-For", "").split(",") + candidates
    network = "unknown"
    for candidate in candidates:
        try:
            network = ipaddress.ip_address(candidate.strip()).compressed
            break
        except ValueError:
            continue
    decisions = [
        consume_limit(db_session, dimension="employee", value=employee, now=datetime.now(UTC), pepper=pepper),
        consume_limit(db_session, dimension="device", value=payload["device_id"], now=datetime.now(UTC), pepper=pepper),
        consume_limit(db_session, dimension="network", value=network, now=datetime.now(UTC), pepper=pepper),
    ]
    exceeded = [decision.retry_after_seconds for decision in decisions if not decision.allowed]
    if exceeded:
        raise ApiError("rate_limited", "Too many authentication attempts.", status=429,
                       retryable=True, details={"retry_after_seconds": max(exceeded)})


def _closed_optional_body(fields: set[str]) -> dict:
    if not request.data:
        return {}
    return _json_object(fields)


def _idempotency_key() -> str:
    value = request.headers.get("Idempotency-Key", "")
    if not value:
        raise ApiError("validation_failed", "Idempotency-Key is required.", status=400)
    return value


def _mutation(action: str, payload: dict, operation):
    actor = current_actor()
    now = datetime.now(UTC)
    db_session = current_request_session()
    try:
        try:
            claim = claim_idempotency(
                db_session, actor, key=_idempotency_key(), action=action,
                request_sha256=request_digest(payload), now=now,
            )
        except RequestInProgress as error:
            raise ApiError("request_in_progress", str(error), status=409, retryable=True) from None
        except IdempotencyConflict as error:
            raise ApiError("idempotency_conflict", str(error), status=409) from None
        except ValueError as error:
            raise ApiError("validation_failed", str(error), status=400) from None
        if claim.replayed:
            reference = claim.response_reference or {}
            if reference.get("one_time_value_unavailable") is True:
                raise ApiError(
                    "idempotent_response_unavailable",
                    "The one-time response is no longer available; sign in again.",
                    status=409,
                )
            return success(reference, status=claim.response_status or 200)
        data, reference = operation(db_session, actor, now)
        complete_idempotency(
            db_session, claim, response_status=200,
            response_reference=reference, now=now,
        )
        db_session.commit()
        g.identity_db_committed = True
        return success(data)
    except InvalidCredentials as error:
        db_session.rollback()
        raise ApiError("invalid_credentials", str(error), status=401) from None
    except SessionReauthenticationRequired as error:
        db_session.rollback()
        raise ApiError("session_reauthentication_required", str(error), status=401) from None
    except ValueError as error:
        db_session.rollback()
        raise ApiError("validation_failed", str(error), status=400) from None
    except ApiError:
        db_session.rollback()
        raise
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db_session.rollback()
        raise ApiError("dependency_unavailable", "Authentication is temporarily unavailable.",
                       status=503, retryable=True) from None


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
    pending_rate_error: ApiError | None = None
    pair = None
    try:
        with session_scope() as db_session:
            try:
                _consume_login_limits(db_session, payload, settings)
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
            except ApiError as error:
                pending_rate_error = error
    except (DatabaseUnavailable, SQLAlchemyError):
        raise ApiError(
            "dependency_unavailable",
            "Authentication is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    if pending_error is not None:
        raise ApiError("invalid_credentials", str(pending_error), status=401)
    if pending_rate_error is not None:
        raise pending_rate_error
    if pair is None:
        raise ApiError("dependency_unavailable", "Authentication is temporarily unavailable.", status=503, retryable=True)
    return success(_token_data(pair))


@auth_bp.post("/logout", endpoint="logout")
@require_access_token
@require_compatible_write
def logout_route():
    payload = _closed_optional_body(set())

    def operation(db_session, actor, now):
        revoke_session(
            db_session, actor_account_id=actor.account_id,
            target_session_id=actor.session_id, now=now,
            audit_writer=current_app.config["AUDIT_WRITER"], request_id=request_id(),
        )
        return {"signed_out": True}, {"signed_out": True}

    return _mutation("auth.logout", payload, operation)


@auth_bp.post("/logout-all", endpoint="logout_all")
@require_access_token
@require_compatible_write
def logout_all_route():
    payload = _closed_optional_body(set())

    def operation(db_session, actor, now):
        count = logout_all(
            db_session, account_id=actor.account_id, now=now,
            audit_writer=current_app.config["AUDIT_WRITER"], request_id=request_id(),
        )
        data = {"signed_out_account_id": str(actor.account_id), "session_count": count}
        return data, data

    return _mutation("auth.logout_all", payload, operation)


@auth_bp.post("/change-pin", endpoint="change_pin")
@require_access_token
@require_compatible_write
def change_pin_route():
    payload = _json_object({"current_pin", "new_pin"})
    settings: IdentitySettings = current_app.config["IDENTITY_SETTINGS"]
    device_id = _validated_device_id(
        {"device_id": request.headers.get("X-Device-ID", "")}, settings
    )

    def operation(db_session, actor, now):
        pair = change_pin(
            db_session, account_id=actor.account_id, current_session_id=actor.session_id,
            current_pin=_required_string(payload, "current_pin"),
            new_pin=_required_string(payload, "new_pin"), device_id=device_id,
            now=now, settings=settings, audit_writer=current_app.config["AUDIT_WRITER"],
            request_id=request_id(),
        )
        return _token_data(pair), {
            "session_id": str(pair.session_id), "one_time_value_unavailable": True,
        }

    return _mutation("auth.change_pin", payload, operation)


@auth_bp.get("/sessions", endpoint="sessions")
@require_access_token
def sessions_route():
    actor = current_actor()
    try:
        db_session = current_request_session()
        rows = list_sessions(
            db_session, account_id=actor.account_id, current_session_id=actor.session_id
        )
        return success([
            {
                "session_id": str(row.session_id), "device_label": row.device_label,
                "persistent": row.persistent, "created_at": _timestamp(row.created_at),
                "last_used_at": _timestamp(row.last_used_at),
                "renewal_expires_at": _timestamp(row.renewal_expires_at), "current": row.current,
            }
            for row in rows
        ])
    except (DatabaseUnavailable, SQLAlchemyError):
        raise ApiError("dependency_unavailable", "Authentication is temporarily unavailable.",
                       status=503, retryable=True) from None


@auth_bp.delete("/sessions/<uuid:session_id>", endpoint="delete_session")
@require_access_token
@require_compatible_write
def delete_session_route(session_id: UUID):
    payload = {"session_id": str(session_id)}

    def operation(db_session, actor, now):
        revoke_session(
            db_session, actor_account_id=actor.account_id, target_session_id=session_id,
            now=now, audit_writer=current_app.config["AUDIT_WRITER"], request_id=request_id(),
        )
        return {"session_id": str(session_id), "revoked": True}, {
            "session_id": str(session_id), "revoked": True,
        }

    return _mutation("auth.revoke_session", payload, operation)


@auth_bp.post("/admin-step-up", endpoint="admin_step_up")
@require_access_token
@require_role("admin")
@require_compatible_write
def admin_step_up_route():
    payload = _json_object({"pin", "purpose"})
    pin = _validated_pin({"pin": payload["pin"]})
    purpose = _required_string(payload, "purpose")
    actor = current_actor()
    db_session = current_request_session()
    now = datetime.now(UTC)
    claim = None
    try:
        canonical = {"session_id": str(actor.session_id), "purpose": purpose}
        try:
            claim = claim_idempotency(
                db_session, actor, key=_idempotency_key(), action="auth.admin_step_up",
                request_sha256=request_digest(canonical), now=now,
            )
        except RequestInProgress as error:
            raise ApiError("request_in_progress", str(error), status=409, retryable=True) from None
        except IdempotencyConflict as error:
            raise ApiError("idempotency_conflict", str(error), status=409) from None
        if claim.replayed:
            reference = claim.response_reference or {}
            if reference.get("one_time_value_unavailable"):
                raise ApiError("idempotent_response_unavailable",
                               "The one-time response is no longer available.", status=409)
            return success(reference)
        result = confirm_admin_pin(
            db_session, actor=actor, pin=pin, purpose=purpose, now=now,
            audit_writer=current_app.config["AUDIT_WRITER"], request_id=request_id(),
        )
        data = {
            "purpose": result.purpose,
            "elevation_expires_at": _timestamp(result.elevation_expires_at),
        }
        reference = dict(data)
        if result.step_up_token is not None:
            data["step_up_token"] = result.step_up_token
            data["step_up_expires_at"] = _timestamp(result.step_up_expires_at)
            reference = {
                "purpose": result.purpose,
                "elevation_expires_at": data["elevation_expires_at"],
                "one_time_value_unavailable": True,
            }
        complete_idempotency(
            db_session, claim, response_status=200, response_reference=reference, now=now,
        )
        db_session.commit()
        return success(data)
    except StepUpRequired as error:
        try:
            if claim is not None and not claim.replayed:
                record = db_session.get(IdempotencyRecord, claim.record_id)
                if record is not None:
                    db_session.delete(record)
            db_session.commit()
        except (SQLAlchemyError, RuntimeError):
            db_session.rollback()
            raise ApiError(
                "dependency_unavailable", "Authentication is temporarily unavailable.",
                status=503, retryable=True,
            ) from None
        raise ApiError("step_up_required", str(error), status=403) from None
    except ApiError:
        db_session.rollback()
        raise
    except ValueError as error:
        db_session.rollback()
        raise ApiError("validation_failed", str(error), status=400) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db_session.rollback()
        raise ApiError("dependency_unavailable", "Authentication is temporarily unavailable.",
                       status=503, retryable=True) from None




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
