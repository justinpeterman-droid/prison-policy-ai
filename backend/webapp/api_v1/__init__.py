import json
import logging

from flask import Blueprint, current_app, g, request

from backend.identity.config import IdentitySettings
from backend.webapp.api_v1.client_policy import policy_data
from backend.webapp.api_v1.context import begin_request, request_event
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.responses import failure, success
from backend.identity.audit import PostgresAuditWriter
from backend.webapp.api_v1.middleware import (
    close_request_session,
    current_actor,
    current_request_session,
    require_access_token,
)
from backend.persistence.database import DatabaseUnavailable, session_scope
from backend.persistence.models import Account, StaffMember
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError


api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")
logger = logging.getLogger("backend.webapp.api_v1")


@api_v1_bp.record_once
def configure_api(state):
    state.app.config.setdefault("AUDIT_WRITER", PostgresAuditWriter())


@api_v1_bp.teardown_request
def close_api_request(error=None):
    close_request_session(error)


@api_v1_bp.before_request
def prepare_api_request():
    begin_request()
    endpoint = (g.get("api_action") or "").strip()
    g.api_action = endpoint or {
        "api_v1.client_policy": "client_policy",
        "api_v1.me": "self_read",
        "api_v1.auth_api.login": "auth_login",
        "api_v1.auth_api.renew": "auth_renew",
        "api_v1.auth_api.logout": "auth_logout",
        "api_v1.auth_api.logout_all": "auth_logout_all",
        "api_v1.auth_api.change_pin": "auth_change_pin",
        "api_v1.auth_api.sessions": "auth_sessions",
        "api_v1.auth_api.delete_session": "auth_revoke_session",
        "api_v1.auth_api.admin_step_up": "auth_admin_step_up",
        "api_v1.admin_api.staff_list": "admin_staff_list",
        "api_v1.admin_api.staff_create": "admin_staff_create",
        "api_v1.admin_api.staff_update": "admin_staff_update",
        "api_v1.admin_api.account_list": "admin_account_list",
        "api_v1.admin_api.account_create": "admin_account_create",
        "api_v1.admin_api.account_update": "admin_account_update",
        "api_v1.admin_api.account_reset_pin": "admin_account_reset_pin",
        "api_v1.admin_api.account_unlock": "admin_account_unlock",
        "api_v1.admin_api.account_sessions": "admin_account_sessions",
        "api_v1.admin_api.account_revoke_sessions": "admin_account_revoke_sessions",
        "api_v1.staff_api.staff_list": "staff_list",
        "api_v1.incidents_api.create": "incident_create",
        "api_v1.incidents_api.get": "incident_read",
        "api_v1.incidents_api.save": "incident_save",
        "api_v1.incidents_api.revision_list": "incident_revision_list",
        "api_v1.incidents_api.revision_detail": "incident_revision_read",
        "api_v1.incidents_api.restore": "incident_restore",
        "api_v1.reports_api.list": "report_list",
        "api_v1.reports_api.get": "report_read",
        "api_v1.reports_api.save": "report_save",
        "api_v1.reports_api.revision_list": "report_revision_list",
        "api_v1.reports_api.revision_detail": "report_revision_read",
        "api_v1.reports_api.restore": "report_restore",
        "api_v1.reports_api.recovery": "report_recovery",
        "api_v1.admin_reports_api.search": "admin_report_search",
        "api_v1.admin_reports_api.detail": "admin_report_read",
        "api_v1.admin_reports_api.revision_list": "admin_report_revision_list",
        "api_v1.admin_reports_api.revision_detail": "admin_report_revision_read",
        "api_v1.admin_reports_api.edit": "admin_report_edit",
        "api_v1.admin_reports_api.restore": "admin_report_restore",
        "api_v1.admin_reports_api.transfer": "admin_report_transfer",
    }.get(request.endpoint or "", "unknown")
    if request.endpoint != "api_v1.client_policy":
        if getattr(g, "client_version", None) is None:
            raise ApiError(
                "validation_failed",
                "X-Client-Version must be a public major.minor.patch version.",
                status=400,
            )


@api_v1_bp.after_request
def record_api_request(response):
    code = getattr(g, "api_error_code", None)
    event = request_event(
        action=getattr(g, "api_action", "unknown"),
        result="success" if response.status_code < 400 else "error",
        status_code=response.status_code,
        error_code=code,
        dependency=getattr(g, "api_dependency", "none"),
    )
    logger.info(json.dumps(event, separators=(",", ":"), sort_keys=True))
    return response


@api_v1_bp.errorhandler(ApiError)
def handle_api_error(error: ApiError):
    g.identity_db_failed = True
    g.api_error_code = error.code
    response = failure(
        error.code,
        error.message,
        error.status,
        retryable=error.retryable,
        details=error.details,
    )
    if error.code == "rate_limited" and error.details:
        retry_after = error.details.get("retry_after_seconds")
        if isinstance(retry_after, int) and retry_after > 0:
            response.headers["Retry-After"] = str(retry_after)
    return response


@api_v1_bp.errorhandler(Exception)
def handle_unexpected_api_error(_error: Exception):
    g.identity_db_failed = True
    g.api_error_code = "internal_error"
    logger.error("Unhandled API exception", extra={"request_id": g.request_id})
    return failure(
        "internal_error",
        "An unexpected error occurred.",
        500,
        retryable=False,
    )


@api_v1_bp.get("/client-policy", endpoint="client_policy")
def client_policy():
    settings: IdentitySettings = current_app.config["IDENTITY_SETTINGS"]
    return success(policy_data(settings))


from backend.webapp.api_v1.auth import auth_bp

api_v1_bp.register_blueprint(auth_bp, url_prefix="/auth")

from backend.webapp.api_v1.admin import admin_bp

api_v1_bp.register_blueprint(admin_bp, url_prefix="/admin")

from backend.webapp.api_v1.staff import staff_bp

api_v1_bp.register_blueprint(staff_bp, url_prefix="/staff")

from backend.webapp.api_v1.incidents import incidents_bp

api_v1_bp.register_blueprint(incidents_bp, url_prefix="/incidents")

from backend.webapp.api_v1.reports import reports_bp

api_v1_bp.register_blueprint(reports_bp, url_prefix="/reports")

from backend.webapp.api_v1.admin_reports import admin_reports_bp

api_v1_bp.register_blueprint(admin_reports_bp, url_prefix="/admin/reports")


@api_v1_bp.get("/me", endpoint="me")
@require_access_token
def me():
    actor = current_actor()
    try:
        db_session = current_request_session()
        account = db_session.scalar(select(Account).where(Account.id == actor.account_id))
        staff = db_session.scalar(select(StaffMember).where(StaffMember.id == actor.staff_member_id))
        if account is None or staff is None:
            raise ApiError("authentication_required", "Authentication is required.", status=401)
        return success({
            "account_id": str(actor.account_id),
            "staff_id": str(actor.staff_member_id),
            "session_id": str(actor.session_id),
            "employee_number": staff.employee_number,
            "display_name": " ".join(
                part for part in (staff.rank, staff.first_name, staff.last_name) if part
            ),
            "rank": staff.rank,
            "shift": staff.shift,
            "role": account.role,
            "status": account.status,
            "must_change_pin": account.must_change_pin,
        })
    except (DatabaseUnavailable, SQLAlchemyError):
        raise ApiError(
            "dependency_unavailable", "Authentication is temporarily unavailable.",
            status=503, retryable=True,
        ) from None
