"""Cookie-authenticated API used only by the Guided Operations web client."""
import json
import logging
import re
from time import perf_counter
from uuid import uuid4

from flask import Blueprint, g, request

from backend.webapp.api_v1.responses import failure
from backend.webapp.web_api.middleware import close_browser_request


web_api_bp = Blueprint("web_api", __name__, url_prefix="/api/web/v1")
logger = logging.getLogger("backend.webapp.web_api")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?$")


@web_api_bp.before_request
def begin_web_request():
    supplied = request.headers.get("X-Request-ID", "")
    g.request_id = supplied if _REQUEST_ID.fullmatch(supplied) else str(uuid4())
    version = request.headers.get("X-Client-Version", "0.1.0")
    g.client_version = version if _VERSION.fullmatch(version) else "invalid"
    g.web_request_started = perf_counter()
    g.web_action = request.endpoint or "unknown"


@web_api_bp.teardown_request
def close_web_request(error=None):
    close_browser_request(error)


@web_api_bp.after_request
def record_web_request(response):
    elapsed = max(0.0, perf_counter() - getattr(g, "web_request_started", perf_counter()))
    event = {
        "request_id": g.request_id,
        "action": str(getattr(g, "web_action", "unknown"))[:96],
        "result": "success" if response.status_code < 400 else "error",
        "http_status_class": f"{response.status_code // 100}xx",
        "latency_bucket": (
            "lt_100ms" if elapsed < 0.1 else
            "lt_500ms" if elapsed < 0.5 else
            "lt_2s" if elapsed < 2 else
            "gte_2s"
        ),
        "error_code": getattr(g, "api_error_code", None),
        "client_version": g.client_version,
    }
    logger.info(json.dumps(event, separators=(",", ":"), sort_keys=True))
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Request-ID"] = g.request_id
    return response


@web_api_bp.errorhandler(Exception)
def handle_unexpected_web_error(_error):
    g.browser_db_failed = True
    g.api_error_code = "internal_error"
    logger.error("Unhandled web API exception", extra={"request_id": g.request_id})
    return failure(
        "internal_error",
        "An unexpected error occurred.",
        500,
        retryable=False,
    )


from backend.webapp.web_api.auth import auth_bp

web_api_bp.register_blueprint(auth_bp, url_prefix="/auth")
