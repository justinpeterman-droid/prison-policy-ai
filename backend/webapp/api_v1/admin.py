from datetime import UTC, datetime
from functools import wraps
from uuid import UUID

from flask import Blueprint, current_app, g, request
from sqlalchemy import select
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
from backend.identity.elevation import (
    AdminElevationRequired,
    StepUpRequired,
    consume_step_up,
    touch_admin_elevation,
)
from backend.identity.browser_handoffs import HandoffInvalid, issue_browser_handoff
from backend.identity.idempotency import (
    IdempotencyConflict,
    RequestInProgress,
    claim_idempotency,
    complete_idempotency,
    request_digest,
)
from backend.persistence.database import DatabaseUnavailable
from backend.persistence.models.identity import Account, StaffMember
from backend.webapp.api_v1.client_policy import require_compatible_write
from backend.webapp.api_v1.context import request_id
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.middleware import (
    current_actor,
    current_request_session,
    require_access_token,
    require_admin_elevation,
    require_role,
    require_step_up,
)
from backend.webapp.api_v1.pagination import (
    decode_cursor,
    encode_cursor,
    parse_page_size,
)
from backend.webapp.api_v1.responses import success


admin_bp = Blueprint("admin_api", __name__)


def _timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _json_object(
    *, exact: set[str] | None = None, allowed: set[str] | None = None
) -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError("validation_failed", "The request body is invalid.", status=400)
    keys = set(payload)
    if (exact is not None and keys != exact) or (
        allowed is not None and (not keys or not keys <= allowed)
    ):
        raise ApiError("validation_failed", "The request body is invalid.", status=400)
    return payload


def _staff_data(row: StaffMember) -> dict[str, object]:
    return {
        "staff_id": str(row.id),
        "employee_number": row.employee_number,
        "rank": row.rank,
        "first_name": row.first_name,
        "last_name": row.last_name,
        "shift": row.shift,
        "is_active": row.is_active,
        "created_at": _timestamp(row.created_at),
        "updated_at": _timestamp(row.updated_at),
    }


def _account_data(row: Account) -> dict[str, object]:
    return {
        "account_id": str(row.id),
        "staff_id": str(row.staff_member_id),
        "role": row.role,
        "status": row.status,
        "must_change_pin": row.must_change_pin,
        "created_at": _timestamp(row.created_at),
        "updated_at": _timestamp(row.updated_at),
    }


def _cursor_key() -> str:
    key = current_app.config["IDENTITY_SETTINGS"].cursor_signing_key
    if not key:
        raise ApiError(
            "dependency_unavailable",
            "Pagination is temporarily unavailable.",
            status=503,
            retryable=True,
        )
    return key


def _rehydrate_replay(db_session, action: str, reference: dict) -> dict:
    if action in {"admin.staff_create", "admin.staff_update"}:
        try:
            staff_id = UUID(str(reference["staff_id"]))
        except (KeyError, ValueError):
            raise RuntimeError("idempotency reference is invalid") from None
        row = db_session.get(StaffMember, staff_id)
        if row is None:
            raise RuntimeError("idempotency target is unavailable")
        return _staff_data(row)
    if action in {"admin.account_update", "admin.account_unlock"}:
        try:
            account_id = UUID(str(reference["account_id"]))
        except (KeyError, ValueError):
            raise RuntimeError("idempotency reference is invalid") from None
        row = db_session.get(Account, account_id)
        if row is None:
            raise RuntimeError("idempotency target is unavailable")
        return _account_data(row)
    return reference


def _page_inputs() -> tuple[int, dict | None]:
    try:
        limit = parse_page_size(request.args.get("limit", "50"))
        cursor = request.args.get("cursor")
        return limit, decode_cursor(cursor, _cursor_key()) if cursor else None
    except ValueError:
        raise ApiError(
            "validation_failed", "Pagination input is invalid.", status=400
        ) from None


def _mutation(
    action: str,
    purpose: str,
    payload: dict,
    operation,
    *,
    response_status: int = 200,
    one_time_replay: bool = False,
    operation_consumes_step_up: bool = False,
):
    actor = current_actor()
    db_session = current_request_session()
    now = datetime.now(UTC)
    try:
        pending = getattr(g, "pending_step_up", None)
        if not pending or pending[0] != purpose:
            raise StepUpRequired("Administrator PIN confirmation is required.")
        if not operation_consumes_step_up:
            consume_step_up(
                db_session,
                actor=actor,
                raw_token=pending[1],
                purpose=purpose,
                now=now,
            )
        try:
            claim = claim_idempotency(
                db_session,
                actor,
                key=request.headers.get("Idempotency-Key", ""),
                action=action,
                request_sha256=request_digest(payload),
                now=now,
            )
        except RequestInProgress as error:
            raise ApiError(
                "request_in_progress", str(error), status=409, retryable=True
            ) from None
        except IdempotencyConflict as error:
            raise ApiError("idempotency_conflict", str(error), status=409) from None
        if claim.replayed:
            if one_time_replay:
                if operation_consumes_step_up:
                    touch_admin_elevation(db_session, actor, now)
                    consume_step_up(
                        db_session,
                        actor=actor,
                        raw_token=pending[1],
                        purpose=purpose,
                        now=now,
                    )
                db_session.commit()
                raise ApiError(
                    "idempotent_response_unavailable",
                    "The one-time value cannot be replayed; request a new value.",
                    status=409,
                )
            replay_data = _rehydrate_replay(
                db_session, action, claim.response_reference or {}
            )
            db_session.commit()
            return success(replay_data, status=claim.response_status or 200)
        data, stable_reference = operation(db_session, actor, now, claim.record_id)
        complete_idempotency(
            db_session,
            claim,
            response_status=response_status,
            response_reference=stable_reference,
            now=now,
        )
        db_session.commit()
        return success(data, status=response_status)
    except StepUpRequired as error:
        db_session.rollback()
        raise ApiError("step_up_required", str(error), status=403) from None
    except AdminElevationRequired as error:
        db_session.rollback()
        raise ApiError("admin_elevation_required", str(error), status=403) from None
    except HandoffInvalid as error:
        db_session.rollback()
        raise ApiError("permission_denied", str(error), status=403) from None
    except DuplicateEmployeeNumberError as error:
        db_session.rollback()
        raise ApiError(error.code, str(error), status=409) from None
    except AccountAlreadyExistsError as error:
        db_session.rollback()
        raise ApiError(error.code, str(error), status=409) from None
    except LastActiveAdminError as error:
        db_session.rollback()
        raise ApiError(error.code, str(error), status=409) from None
    except AccountConflictError as error:
        db_session.rollback()
        raise ApiError(error.code, str(error), status=409) from None
    except LookupError as error:
        db_session.rollback()
        raise ApiError("not_found", str(error), status=404) from None
    except ApiError:
        db_session.rollback()
        raise
    except IntegrityError:
        db_session.rollback()
        raise ApiError(
            "account_conflict", "The account changed; reload and try again.", status=409
        ) from None
    except OperationalError as error:
        db_session.rollback()
        sqlstate = getattr(getattr(error, "orig", None), "sqlstate", None)
        if sqlstate in {"40P01", "40001", "55P03"}:
            raise ApiError(
                "account_conflict",
                "The account is busy; reload and try again.",
                status=409,
            ) from None
        raise ApiError(
            "dependency_unavailable",
            "The Admin service is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None
    except ValueError as error:
        db_session.rollback()
        raise ApiError("validation_failed", str(error), status=400) from None
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        db_session.rollback()
        raise ApiError(
            "dependency_unavailable",
            "The Admin service is temporarily unavailable.",
            status=503,
            retryable=True,
        ) from None


def _admin_get(view):
    @wraps(view)
    def safe(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except ApiError:
            raise
        except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
            raise ApiError(
                "dependency_unavailable",
                "The Admin service is temporarily unavailable.",
                status=503,
                retryable=True,
            ) from None

    return require_access_token(require_role("admin")(require_admin_elevation(safe)))


@admin_bp.get("/staff", endpoint="staff_list")
@_admin_get
def staff_list_route():
    limit, cursor = _page_inputs()
    page = list_staff(
        current_request_session(),
        cursor=cursor,
        limit=limit,
        query=request.args.get("query"),
    )
    return success(
        {
            "items": [_staff_data(row) for row in page.items],
            "next_cursor": encode_cursor(page.next_cursor, _cursor_key())
            if page.next_cursor
            else None,
        }
    )


@admin_bp.post("/staff", endpoint="staff_create")
@require_access_token
@require_role("admin")
@require_compatible_write
@require_step_up("staff_write")
@require_admin_elevation
def staff_create_route():
    payload = _json_object(
        exact={"employee_number", "rank", "first_name", "last_name", "shift"}
    )
    return _mutation(
        "admin.staff_create",
        "staff_write",
        payload,
        lambda db, actor, now, _claim: (
            (lambda row: (_staff_data(row), {"staff_id": str(row.id)}))(
                create_staff(
                    db,
                    actor=actor,
                    payload=payload,
                    now=now,
                    audit_writer=current_app.config["AUDIT_WRITER"],
                    request_id=request_id(),
                )
            )
        ),
    )


@admin_bp.patch("/staff/<uuid:staff_id>", endpoint="staff_update")
@require_access_token
@require_role("admin")
@require_compatible_write
@require_step_up("staff_write")
@require_admin_elevation
def staff_update_route(staff_id: UUID):
    payload = _json_object(
        allowed={
            "employee_number",
            "rank",
            "first_name",
            "last_name",
            "shift",
            "is_active",
        }
    )
    return _mutation(
        "admin.staff_update",
        "staff_write",
        {"staff_id": str(staff_id), **payload},
        lambda db, actor, now, _claim: (
            (lambda row: (_staff_data(row), {"staff_id": str(row.id)}))(
                update_staff(
                    db,
                    actor=actor,
                    staff_id=staff_id,
                    payload=payload,
                    now=now,
                    audit_writer=current_app.config["AUDIT_WRITER"],
                    request_id=request_id(),
                )
            )
        ),
    )


@admin_bp.get("/accounts", endpoint="account_list")
@_admin_get
def account_list_route():
    limit, cursor = _page_inputs()
    page = list_accounts(current_request_session(), cursor=cursor, limit=limit)
    return success(
        {
            "items": [_account_data(row) for row in page.items],
            "next_cursor": encode_cursor(page.next_cursor, _cursor_key())
            if page.next_cursor
            else None,
        }
    )


@admin_bp.post("/accounts", endpoint="account_create")
@require_access_token
@require_role("admin")
@require_compatible_write
@require_step_up("account_create")
@require_admin_elevation
def account_create_route():
    payload = _json_object(exact={"staff_id", "role"})
    try:
        staff_id = UUID(payload["staff_id"])
    except (TypeError, ValueError):
        raise ApiError(
            "validation_failed", "The request body is invalid.", status=400
        ) from None

    def operation(db, actor, now, claim_id):
        result = create_account_for_staff(
            db,
            actor=actor,
            staff_id=staff_id,
            role=payload["role"],
            now=now,
            audit_writer=current_app.config["AUDIT_WRITER"],
            request_id=request_id(),
        )
        data = {
            "operation_reference_id": str(claim_id),
            "account_id": str(result.account_id),
            "temporary_pin": result.temporary_pin,
            "one_time_value_unavailable": False,
        }
        stable = {
            "operation_reference_id": str(claim_id),
            "account_id": str(result.account_id),
            "one_time_value_unavailable": True,
        }
        return data, stable

    return _mutation("admin.account_create", "account_create", payload, operation)


@admin_bp.patch("/accounts/<uuid:account_id>", endpoint="account_update")
@require_access_token
@require_role("admin")
@require_compatible_write
@require_step_up("account_role_status")
@require_admin_elevation
def account_update_route(account_id: UUID):
    payload = _json_object(exact={"role", "status"})
    combined = {"account_id": str(account_id), **payload}
    return _mutation(
        "admin.account_update",
        "account_role_status",
        combined,
        lambda db, actor, now, _claim: (
            (
                lambda row: (
                    _account_data(row),
                    {"account_id": str(row.id), "role": row.role, "status": row.status},
                )
            )(
                change_account_role_or_status(
                    db,
                    actor=actor,
                    target_account_id=account_id,
                    role=payload["role"],
                    status=payload["status"],
                    now=now,
                    audit_writer=current_app.config["AUDIT_WRITER"],
                    request_id=request_id(),
                )
            )
        ),
    )


@admin_bp.post("/accounts/<uuid:account_id>/reset-pin", endpoint="account_reset_pin")
@require_access_token
@require_role("admin")
@require_compatible_write
@require_step_up("account_reset_pin")
@require_admin_elevation
def account_reset_pin_route(account_id: UUID):
    if request.data:
        raise ApiError(
            "validation_failed", "This operation does not accept a body.", status=400
        )
    payload = {"account_id": str(account_id)}

    def operation(db, actor, now, claim_id):
        result = reset_account_pin(
            db,
            actor=actor,
            target_account_id=account_id,
            now=now,
            audit_writer=current_app.config["AUDIT_WRITER"],
            request_id=request_id(),
        )
        data = {
            "operation_reference_id": str(claim_id),
            "account_id": str(result.account_id),
            "temporary_pin": result.temporary_pin,
            "one_time_value_unavailable": False,
        }
        stable = {
            "operation_reference_id": str(claim_id),
            "account_id": str(result.account_id),
            "one_time_value_unavailable": True,
        }
        return data, stable

    return _mutation("admin.account_reset_pin", "account_reset_pin", payload, operation)


@admin_bp.post("/accounts/<uuid:account_id>/unlock", endpoint="account_unlock")
@require_access_token
@require_role("admin")
@require_compatible_write
@require_step_up("account_unlock")
@require_admin_elevation
def account_unlock_route(account_id: UUID):
    if request.data:
        raise ApiError(
            "validation_failed", "This operation does not accept a body.", status=400
        )
    payload = {"account_id": str(account_id)}

    def operation(db, actor, now, _claim):
        row = unlock_account(
            db,
            actor=actor,
            target_account_id=account_id,
            now=now,
            audit_writer=current_app.config["AUDIT_WRITER"],
            request_id=request_id(),
        )
        if row is None:
            raise LookupError("account not found")
        return (
            _account_data(row),
            {"account_id": str(row.id), "status": row.status},
        )

    return _mutation(
        "admin.account_unlock",
        "account_unlock",
        payload,
        operation,
    )


@admin_bp.get("/accounts/<uuid:account_id>/sessions", endpoint="account_sessions")
@_admin_get
def account_sessions_route(account_id: UUID):
    db = current_request_session()
    if db.scalar(select(Account.id).where(Account.id == account_id)) is None:
        raise ApiError("not_found", "Account not found.", status=404)
    limit, cursor = _page_inputs()
    page = list_account_sessions(db, account_id=account_id, cursor=cursor, limit=limit)
    actor = current_actor()
    return success(
        {
            "account_id": str(account_id),
            "items": [
                {
                    "session_id": str(row.id),
                    "device_label": row.device_label,
                    "persistent": row.persistent,
                    "created_at": _timestamp(row.created_at),
                    "last_used_at": _timestamp(row.last_used_at),
                    "idle_expires_at": _timestamp(row.renewal_expires_at),
                    "revoked_at": _timestamp(row.revoked_at),
                    "current": row.id == actor.session_id,
                }
                for row in page.items
            ],
            "next_cursor": encode_cursor(page.next_cursor, _cursor_key())
            if page.next_cursor
            else None,
        }
    )


@admin_bp.post(
    "/accounts/<uuid:account_id>/revoke-sessions", endpoint="account_revoke_sessions"
)
@require_access_token
@require_role("admin")
@require_compatible_write
@require_step_up("account_revoke_sessions")
@require_admin_elevation
def account_revoke_sessions_route(account_id: UUID):
    payload = _json_object(allowed={"scope", "session_id"})
    scope = payload.get("scope")
    if scope == "all" and set(payload) == {"scope"}:
        session_id = None
    elif scope == "one" and set(payload) == {"scope", "session_id"}:
        try:
            session_id = UUID(payload["session_id"])
        except (TypeError, ValueError):
            raise ApiError(
                "validation_failed", "The request body is invalid.", status=400
            ) from None
    else:
        raise ApiError("validation_failed", "The request body is invalid.", status=400)
    canonical = {"account_id": str(account_id), **payload}

    def operation(db, actor, now, _claim_id):
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
            "scope": scope,
            "revoked_session_ids": [str(value) for value in revoked],
            "revoked_count": len(revoked),
        }
        return data, data

    return _mutation(
        "admin.account_revoke_sessions", "account_revoke_sessions", canonical, operation
    )


@admin_bp.post("/review-lab-handoffs", endpoint="review_lab_handoff_issue")
@require_access_token
@require_role("admin")
@require_compatible_write
@require_step_up("review_lab_handoff")
def review_lab_handoff_issue_route():
    g.api_action = "admin_review_lab_handoff_issue"
    if request.data:
        raise ApiError(
            "validation_failed", "This operation does not accept a body.", status=400
        )

    def operation(db, actor, now, _claim_id):
        result = issue_browser_handoff(
            db,
            actor=actor,
            now=now,
            audit_writer=current_app.config["AUDIT_WRITER"],
            request_id=request_id(),
            step_up_token=g.pending_step_up[1],
        )
        origin = current_app.config["IDENTITY_SETTINGS"].review_lab_origin
        if not origin:
            raise RuntimeError("Review Lab origin is unavailable")
        data = {
            "handoff_url": f"{origin}/access-handoff#{result.token}",
            "expires_at": _timestamp(result.expires_at),
        }
        return data, {
            "handoff_id": str(result.handoff_id),
            "one_time_value_unavailable": True,
        }

    return _mutation(
        "admin.review_lab_handoff_issue",
        "review_lab_handoff",
        {},
        operation,
        response_status=201,
        one_time_replay=True,
        operation_consumes_step_up=True,
    )
