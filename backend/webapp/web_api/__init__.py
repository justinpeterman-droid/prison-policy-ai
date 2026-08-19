"""Cookie-authenticated browser API isolated from the Access bearer API."""
import logging
import re
import secrets
from datetime import UTC, datetime

from flask import Blueprint, g, request
from packaging.version import InvalidVersion, Version
from werkzeug.exceptions import HTTPException

from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.responses import failure
from backend.webapp.web_api.middleware import close_browser_request


logger = logging.getLogger(__name__)
web_api_bp = Blueprint("web_api_v1", __name__, url_prefix="/api/web/v1")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")


@web_api_bp.before_request
def begin_browser_request():
    supplied = request.headers.get("X-Request-ID", "")
    g.request_id = supplied if _REQUEST_ID.fullmatch(supplied) else secrets.token_hex(16)
    raw_version = request.headers.get("X-Client-Version", "")
    try:
        g.client_version = Version(raw_version) if raw_version else None
    except InvalidVersion:
        g.client_version = "invalid"
    g.server_time = datetime.now(UTC)
    g.browser_db_failed = False


@web_api_bp.after_request
def secure_browser_response(response):
    response.headers["X-Request-ID"] = str(g.get("request_id", ""))
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    return response


@web_api_bp.teardown_request
def teardown_browser_request(error):
    close_browser_request(error)


@web_api_bp.errorhandler(ApiError)
def handle_browser_api_error(error: ApiError):
    g.browser_db_failed = True
    response = failure(
        error.code,
        error.message,
        error.status,
        error.retryable,
        error.details,
    )
    if error.code == "rate_limited" and error.details:
        retry_after = error.details.get("retry_after_seconds")
        if isinstance(retry_after, int) and retry_after > 0:
            response.headers["Retry-After"] = str(retry_after)
    return response


@web_api_bp.errorhandler(Exception)
def handle_unexpected_browser_error(error):
    g.browser_db_failed = True
    if isinstance(error, HTTPException):
        code = "not_found" if error.code == 404 else "http_error"
        return failure(code, error.description, error.code or 500)
    logger.exception(
        "Unhandled browser API error",
        extra={"request_id": str(g.get("request_id", ""))},
    )
    return failure(
        "internal_error",
        "The workspace request could not be completed.",
        500,
        retryable=False,
    )


from backend.webapp.web_api.account import account_bp  # noqa: E402
from backend.webapp.web_api.auth import auth_bp  # noqa: E402
from backend.webapp.web_api.forms import forms_bp  # noqa: E402
from backend.webapp.web_api.forms_library import forms_library_bp  # noqa: E402
from backend.webapp.web_api.home import home_bp  # noqa: E402
from backend.webapp.web_api.incident_records import incident_records_bp  # noqa: E402
from backend.webapp.web_api.incidents import incidents_bp  # noqa: E402
from backend.webapp.web_api.jobs import jobs_bp  # noqa: E402
from backend.webapp.web_api.paperwork import paperwork_bp  # noqa: E402
from backend.webapp.web_api.policy import policy_bp  # noqa: E402
from backend.webapp.web_api.reports import reports_bp  # noqa: E402
from backend.webapp.web_api.staff import staff_bp  # noqa: E402

web_api_bp.register_blueprint(auth_bp, url_prefix="/auth")
web_api_bp.register_blueprint(account_bp, url_prefix="/account")
web_api_bp.register_blueprint(home_bp)
web_api_bp.register_blueprint(incidents_bp, url_prefix="/incidents")
web_api_bp.register_blueprint(incident_records_bp)
web_api_bp.register_blueprint(reports_bp)
web_api_bp.register_blueprint(jobs_bp)
web_api_bp.register_blueprint(forms_bp)
web_api_bp.register_blueprint(forms_library_bp)
web_api_bp.register_blueprint(paperwork_bp)
web_api_bp.register_blueprint(policy_bp, url_prefix="/policy")
web_api_bp.register_blueprint(staff_bp)

__all__ = ["web_api_bp"]
