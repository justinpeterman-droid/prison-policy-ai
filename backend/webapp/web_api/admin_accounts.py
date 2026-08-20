"""Administrator staff and account lifecycle routes for Guided Operations."""
from datetime import UTC, datetime
from uuid import UUID

from flask import Blueprint, current_app, request
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from backend.identity.accounts import (
    AccountAlreadyExistsError,
    AccountConflictError,
    DuplicateEmployeeNumberError,
    LastActiveAdminError,
    change_account_role_or_status,
    create_account_for_staff,
    create_staff,
    list_account_sessions,
    list_accounts,
    list_staff,
    reset_account_pin,
    revoke_account_sessions,
    unlock_account,
    update_staff,
)
from backend.identity.browser_admin import (
    BrowserAdminStepUpRequired,
    consume_browser_admin_step_up,
    require_browser_admin_elevation,
)
from backend.identity.config import IdentitySettings
from backend.identity.elevation import AdminElevationRequired
from backend.identity.idempotency import (
    IdempotencyConflict,
    RequestInProgress,
    claim_idempotency,
    complete_idempotency,
    request_digest,
)
from backend.persistence.database import DatabaseUnavailable
from backend.persistence.models.identity import Account, StaffMember
from backend.webapp.api_v1.context import request_id
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.pagination import InvalidCursor, decode_cursor, encode_cursor
from backend.webapp.api_v1.responses import failure, success
from backend.webapp.web_api.admin_auth import (
    ADMIN_STEP_UP_COOKIE,
    ADMIN_STEP_UP_COOKIE_PATH,
)
from backend.webapp.web_api.auth import _is_https
from backend.webapp.web_api.middleware import (
    current_browser_actor,
    current_browser_session,
    require_browser_csrf,
    require_browser_role,
    require_browser_session,
)


admin_accounts_bp = Blueprint("web_admin_accounts", __name__)


def _timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _settings() -> IdentitySettings:
    settings = current_app.config.get("IDENTITY_SETTINGS")
    if not isinstance(settings, IdentitySettings) or not settings.cursor_signing_key:
        raise ApiError(
            "dependency_unavailable",
            "Administrator account pagination is temporarily unavailable.",
            status=503,
            retryable=True,
        )
    return settings


def _page_inputs() -> tuple[int, dict | None, IdentitySettings]:
    settings = _settings()
    raw_limit = request.args.get("limit", "50")
    if not raw_limit.isascii() or not raw_limit.isdigit():
        raise ApiError("validation_failed", "Pagination input is invalid.", status=400)
    limit = int(raw_limit)
    if not 1 <= limit <= 100:
        raise ApiError("validation_failed", "Pagination input is invalid.", status=400)
    raw_cursor = request.args.get("cursor")
    try:
        cursor = (
            decode_cursor(raw_cursor, settings.cursor_signing_key or "")
            if raw_cursor else None
        )
    except InvalidCursor:
        raise ApiError("validation_failed", "Pagination input is invalid.", status=400) from None
    return limit, cursor, settings


def _account_data(db, row: Account) -> dict[str, object]:
    staff = db.get(StaffMember, row.staff_member_id)
    if staff is None:
        raise RuntimeError("account staff is unavailable")
    return {
        "account_id": str(row.id),
        "staff_id": str(row.staff_member_id),
        "employee_number": staff.employee_number,
        "display_name": " ".join(
            part for part in (staff.rank, staff.first_name, staff.last_name) if part
        ),
        "role": row.role,
        "status": row.status,
        "must_change_pin": row.must_change_pin,
        "created_at": _timestamp(row.created_at),
        "updated_at": _timestamp(row.updated_at),
    }


def _staff_data(db, row: StaffMember) -> dict[str, object]:
    account = db.query(Account).filter(Account.staff_member_id == row.id).one_or_none()
    return {
        "staff_id": str(row.id),
        "employee_number": row.employee_number,
        "rank": row.rank,
        "first_name": row.first_name,
        "last_name": row.last_name,
        "display_name": " ".join(
            part for part in (row.rank, row.first_name, row.last_name) if part
        ),
        "shift": row.shift,
        "is_active": row.is_active,
        "account": _account_data(db, account) if account is not None else None,
        "created_at": _timestamp(row.created_at),
        "updated_at": _timestamp(row.updated_at),
    }


def _session_data(row) -> dict[str, object]:
    return {
        "session_id": str(row.id),
        "device_label": row.device_label,
        "persistent": row.persistent,
        "last_used_at": _timestamp(row.last_used_at),
        "created_at": _timestamp(row.created_at),
        "access_expires_at": _timestamp(row.access_expires_at),
        "renewal_expires_at": _timestamp(row.renewal_expires_at),
        "revoked_at": _timestamp(row.revoked_at),
        "revoke_reason": row.revoke_reason,
    }


def _require_elevation() -> None:
    try:
        require_browser_admin_elevation(
            current_browser_session(),
            actor=current_browser_actor(),
            now=datetime.now(UTC),
        )
    except AdminElevationRequired:
        raise ApiError(
            "admin_elevation_required",
            "Administrator PIN confirmation is required.",
            status=403,
        ) from None


def _consume_step_up(purpose: str) -> None:
    raw = request.cookies.get(ADMIN_STEP_UP_COOKIE, "")
    if not raw:
        raise ApiError(
            "step_up_required",
            "Administrator PIN confirmation is required.",
            status=403,
        )
    try:
        consume_browser_admin_step_up(
            current_browser_session(),
            actor=current_browser_actor(),
            raw_token=raw,
            purpose=purpose,
            now=datetime.now(UTC),
        )
    except BrowserAdminStepUpRequired:
        raise ApiError(
            "step_up_required",
            "Administrator PIN confirmation is required.",
            status=403,
        ) from None


def _clear_step_up(response):
    response.delete_cookie(
        ADMIN_STEP_UP_COOKIE,
        path=ADMIN_STEP_UP_COOKIE_PATH,
        secure=_is_https(),
        httponly=True,
        samesite="Lax",
    )
    return response


def _json_exact(fields: set[str]) -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != fields:
        raise ApiError("validation_failed", "The administrator request is invalid.", status=400)
    return payload


def _json_allowed(fields: set[str]) -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not payload or not set(payload) <= fields:
        raise ApiError("validation_failed", "The administrator request is invalid.", status=400)
    return payload


def _idempotency_key() -> str:
    key = request.headers.get("Idempotency-Key", "")
    if not key:
        raise ApiError("validation_failed", "Idempotency-Key is required.", status=400)
    return key


def _stable_replay(db, action: str, reference: dict) -> dict[str, object]:
    if action in {"admin.staff_create", "admin.staff_update"}:
        row = db.get(StaffMember, UUID(str(reference["staff_id"])))
        if row is None:
            raise RuntimeError("idempotent staff target is unavailable")
        return _staff_data(db, row)
    if action in {"admin.account_update", "admin.account_unlock"}:
        row = db.get(Account, UUID(str(reference["account_id"])))
        if row is None:
            raise RuntimeError("idempotent account target is unavailable")
        return _account_data(db, row)
    if action == "admin.account_revoke_sessions":
        return {
            "account_id": str(reference["account_id"]),
            "revoked_session_ids": list(reference.get("revoked_session_ids", [])),
            "revoked_count": int(reference.get("revoked_count", 0)),
        }
    raise RuntimeError("idempotent response is unavailable")


def _mutation(
    *,
    action: str,
    purpose: str,
    canonical: dict,
    operation,
    one_time: bool = False,
):
    _require_elevation()
    db = current_browser_session()
    actor = current_browser_actor()
    now = datetime.now(UTC)
    try:
        _consume_step_up(purpose)
        claim = claim_idempotency(
            db,
            actor,
            key=_idempotency_key(),
            action=action,
            request_sha256=request_digest(canonical),
            now=now,
        )
        if claim.replayed:
            db.commit()
            if one_time:
                return _clear_step_up(failure(
                    "idempotent_response_unavailable",
                    "The one-time value cannot be replayed; request a new operation.",
                    409,
                ))
            return _clear_step_up(success(_stable_replay(
                db, action, claim.response_reference or {},
            )))

        data, stable_reference = operation(db, actor, now)
        complete_idempotency(
            db,
            claim,
            response_status=200,
            response_reference=stable_reference,
            now=now,
        )
        db.commit()
        return _clear_step_up(success(data))
    except ApiError:
        db.rollback()
        raise
    except RequestInProgress as error:
        db.rollback()
        raise ApiError("request_in_progress", str(error), status=409, retryable=True) from None
    except IdempotencyConflict as error:
        db.rollback()
        raise ApiError("idempotency_conflict", str(error), status=409) from None
    except DuplicateEmployeeNumberError as error:
        db.rollback()
        raise ApiError(error.code, str(error), status=409) from None
    except AccountAlreadyExistsError as error:
        db.rollback()
        raise ApiError(error.code, str(error), status=409) from None
    except LastActiveAdminError as error:
        db.rollback()
        raise ApiError(error.code, str(error), status=409) from None
    except AccountConflictError as error:
        db.rollback()
        raise ApiError(error.code, str(error), status=409) from None
    except LookupError as error:
        db.rollback()
        raise ApiError("not_found", str(error), status=404) from None
    except (ValueError, TypeError):
        db.rollback()
        raise ApiError("validation_failed", "The administrator request is invalid.", status=400) from None
    except IntegrityError:
        db.rollback()
        raise ApiError(
            "account_conflict",
            "The administrator record changed; reload and try again.",
            status=409,
        ) from None
    except OperationalError as error:
        db.rollback()
        sqlstate = getattr(getattr(error, "orig", None), "sqlstate", None)
        if sqlstate in {"40P01", "40001", "55P03"}:
            raise ApiError(
                "account_conflict",
                "The administrator record is busy; reload and try again.",
                status=409,
            ) from None
        raise ApiError(
            "dependency_unavailable",
            "Administrator accounts are temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db.rollback()
        raise ApiError(
            "dependency_unavailable",
            "Administrator accounts are temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


@admin_accounts_bp.get("/staff", endpoint="staff_list")
@require_browser_session
@require_browser_role("admin")
def staff_list_route():
    _require_elevation()
    if set(request.args) - {"query", "limit", "cursor"}:
        raise ApiError("validation_failed", "Staff search is invalid.", status=400)
    limit, cursor, settings = _page_inputs()
    query = request.args.get("query")
    if query is not None and len(query) > 100:
        raise ApiError("validation_failed", "Staff search is invalid.", status=400)
    try:
        page = list_staff(
            current_browser_session(), cursor=cursor, limit=limit, query=query,
        )
    except (ValueError, TypeError):
        raise ApiError("validation_failed", "Staff search is invalid.", status=400) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable", "Staff data is temporarily unavailable.",
            status=503, retryable=True,
        ) from None
    return success({
        "items": [_staff_data(current_browser_session(), row) for row in page.items],
        "next_cursor": (
            encode_cursor(page.next_cursor, settings.cursor_signing_key)
            if page.next_cursor else None
        ),
    })


@admin_accounts_bp.post("/staff", endpoint="staff_create")
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def staff_create_route():
    payload = _json_exact({
        "employee_number", "rank", "first_name", "last_name", "shift",
    })

    def operation(db, actor, now):
        row = create_staff(
            db,
            actor=actor,
            payload=payload,
            now=now,
            audit_writer=current_app.config["AUDIT_WRITER"],
            request_id=request_id(),
        )
        return _staff_data(db, row), {"staff_id": str(row.id)}

    return _mutation(
        action="admin.staff_create",
        purpose="staff_write",
        canonical=payload,
        operation=operation,
    )


@admin_accounts_bp.patch("/staff/<uuid:staff_id>", endpoint="staff_update")
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def staff_update_route(staff_id: UUID):
    payload = _json_allowed({
        "employee_number", "rank", "first_name", "last_name", "shift", "is_active",
    })
    canonical = {"staff_id": str(staff_id), **payload}

    def operation(db, actor, now):
        row = update_staff(
            db,
            actor=actor,
            staff_id=staff_id,
            payload=payload,
            now=now,
            audit_writer=current_app.config["AUDIT_WRITER"],
            request_id=request_id(),
        )
        return _staff_data(db, row), {"staff_id": str(row.id)}

    return _mutation(
        action="admin.staff_update",
        purpose="staff_write",
        canonical=canonical,
        operation=operation,
    )


@admin_accounts_bp.get("/accounts", endpoint="account_list")
@require_browser_session
@require_browser_role("admin")
def account_list_route():
    _require_elevation()
    if set(request.args) - {"limit", "cursor"}:
        raise ApiError("validation_failed", "Account search is invalid.", status=400)
    limit, cursor, settings = _page_inputs()
    try:
        page = list_accounts(current_browser_session(), cursor=cursor, limit=limit)
    except (ValueError, TypeError):
        raise ApiError("validation_failed", "Account search is invalid.", status=400) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable", "Account data is temporarily unavailable.",
            status=503, retryable=True,
        ) from None
    return success({
        "items": [_account_data(current_browser_session(), row) for row in page.items],
        "next_cursor": (
            encode_cursor(page.next_cursor, settings.cursor_signing_key)
            if page.next_cursor else None
        ),
    })


@admin_accounts_bp.post("/accounts", endpoint="account_create")
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def account_create_route():
    payload = _json_exact({"staff_id", "role"})
    try:
        staff_id = UUID(str(payload["staff_id"]))
    except (TypeError, ValueError):
        raise ApiError("validation_failed", "The administrator request is invalid.", status=400) from None

    def operation(db, actor, now):
        result = create_account_for_staff(
            db,
            actor=actor,
            staff_id=staff_id,
            role=payload["role"],
            now=now,
            audit_writer=current_app.config["AUDIT_WRITER"],
            request_id=request_id(),
        )
        return ({
            "account_id": str(result.account_id),
            "staff_id": str(staff_id),
            "temporary_pin": result.temporary_pin,
            "temporary_pin_expires_at": _timestamp(result.expires_at),
        }, {
            "account_id": str(result.account_id),
            "staff_id": str(staff_id),
            "one_time_value_unavailable": True,
        })

    return _mutation(
        action="admin.account_create",
        purpose="account_create",
        canonical={"staff_id": str(staff_id), "role": payload["role"]},
        operation=operation,
        one_time=True,
    )


@admin_accounts_bp.patch("/accounts/<uuid:account_id>", endpoint="account_update")
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def account_update_route(account_id: UUID):
    payload = _json_exact({"role", "status"})
    canonical = {"account_id": str(account_id), **payload}

    def operation(db, actor, now):
        row = change_account_role_or_status(
            db,
            actor=actor,
            target_account_id=account_id,
            role=payload["role"],
            status=payload["status"],
            now=now,
            audit_writer=current_app.config["AUDIT_WRITER"],
            request_id=request_id(),
        )
        return _account_data(db, row), {"account_id": str(row.id)}

    return _mutation(
        action="admin.account_update",
        purpose="account_role_status",
        canonical=canonical,
        operation=operation,
    )


@admin_accounts_bp.post("/accounts/<uuid:account_id>/reset-pin", endpoint="account_reset_pin")
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def account_reset_pin_route(account_id: UUID):
    if request.data:
        raise ApiError("validation_failed", "This operation does not accept a body.", status=400)

    def operation(db, actor, now):
        result = reset_account_pin(
            db,
            actor=actor,
            target_account_id=account_id,
            now=now,
            audit_writer=current_app.config["AUDIT_WRITER"],
            request_id=request_id(),
        )
        return ({
            "account_id": str(result.account_id),
            "temporary_pin": result.temporary_pin,
            "temporary_pin_expires_at": _timestamp(result.expires_at),
        }, {
            "account_id": str(result.account_id),
            "one_time_value_unavailable": True,
        })

    return _mutation(
        action="admin.account_reset_pin",
        purpose="account_reset_pin",
        canonical={"account_id": str(account_id)},
        operation=operation,
        one_time=True,
    )


@admin_accounts_bp.post("/accounts/<uuid:account_id>/unlock", endpoint="account_unlock")
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def account_unlock_route(account_id: UUID):
    if request.data:
        raise ApiError("validation_failed", "This operation does not accept a body.", status=400)

    def operation(db, actor, now):
        row = unlock_account(
            db,
            actor=actor,
            target_account_id=account_id,
            now=now,
            audit_writer=current_app.config["AUDIT_WRITER"],
            request_id=request_id(),
        )
        return _account_data(db, row), {"account_id": str(row.id)}

    return _mutation(
        action="admin.account_unlock",
        purpose="account_unlock",
        canonical={"account_id": str(account_id)},
        operation=operation,
    )


@admin_accounts_bp.get("/accounts/<uuid:account_id>/sessions", endpoint="account_sessions")
@require_browser_session
@require_browser_role("admin")
def account_sessions_route(account_id: UUID):
    _require_elevation()
    if set(request.args) - {"limit", "cursor"}:
        raise ApiError("validation_failed", "Session pagination is invalid.", status=400)
    limit, cursor, settings = _page_inputs()
    if current_browser_session().get(Account, account_id) is None:
        raise ApiError("not_found", "Account not found.", status=404)
    try:
        page = list_account_sessions(
            current_browser_session(), account_id=account_id, cursor=cursor, limit=limit,
        )
    except (ValueError, TypeError):
        raise ApiError("validation_failed", "Session pagination is invalid.", status=400) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        raise ApiError(
            "dependency_unavailable", "Session data is temporarily unavailable.",
            status=503, retryable=True,
        ) from None
    return success({
        "items": [_session_data(row) for row in page.items],
        "next_cursor": (
            encode_cursor(page.next_cursor, settings.cursor_signing_key)
            if page.next_cursor else None
        ),
    })


@admin_accounts_bp.post(
    "/accounts/<uuid:account_id>/revoke-sessions",
    endpoint="account_revoke_sessions",
)
@require_browser_session
@require_browser_csrf
@require_browser_role("admin")
def account_revoke_sessions_route(account_id: UUID):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) not in ({"scope"}, {"scope", "session_id"}):
        raise ApiError("validation_failed", "The administrator request is invalid.", status=400)
    scope = payload.get("scope")
    try:
        session_id = (
            UUID(str(payload["session_id"])) if payload.get("session_id") is not None else None
        )
    except (TypeError, ValueError):
        raise ApiError("validation_failed", "The administrator request is invalid.", status=400) from None
    canonical = {
        "account_id": str(account_id),
        "scope": scope,
        "session_id": str(session_id) if session_id else None,
    }

    def operation(db, actor, now):
        revoked = revoke_account_sessions(
            db,
            actor=actor,
            target_account_id=account_id,
            scope=scope,
            target_session_id=session_id,
            now=now,
            audit_writer=current_app.config["AUDIT_WRITER"],
            request_id=request_id(),
        )
        data = {
            "account_id": str(account_id),
            "revoked_session_ids": [str(value) for value in revoked],
            "revoked_count": len(revoked),
        }
        return data, {
            "account_id": str(account_id),
            "revoked_count": len(revoked),
        }

    return _mutation(
        action="admin.account_revoke_sessions",
        purpose="account_revoke_sessions",
        canonical=canonical,
        operation=operation,
    )