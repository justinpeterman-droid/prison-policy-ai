import json
import logging

from flask import Blueprint, current_app, g, request

from backend.identity.config import IdentitySettings
from backend.webapp.api_v1.client_policy import policy_data
from backend.webapp.api_v1.context import begin_request, request_event
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.responses import failure, success


api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")
logger = logging.getLogger("backend.webapp.api_v1")


@api_v1_bp.before_request
def prepare_api_request():
    begin_request()
    endpoint = (g.get("api_action") or "").strip()
    g.api_action = endpoint or {
        "api_v1.client_policy": "client_policy",
        "api_v1.me": "self_read",
        "api_v1.auth_api.login": "auth_login",
        "api_v1.auth_api.renew": "auth_renew",
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
    g.api_error_code = error.code
    return failure(
        error.code,
        error.message,
        error.status,
        retryable=error.retryable,
        details=error.details,
    )


@api_v1_bp.errorhandler(Exception)
def handle_unexpected_api_error(_error: Exception):
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


@api_v1_bp.get("/me", endpoint="me")
def me():
    raise ApiError(
        "authentication_required",
        "Authentication is required.",
        status=401,
    )


from backend.webapp.api_v1.auth import auth_bp

api_v1_bp.register_blueprint(auth_bp, url_prefix="/auth")
