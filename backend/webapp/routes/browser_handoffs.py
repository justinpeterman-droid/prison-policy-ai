from datetime import UTC, datetime

from flask import Blueprint, current_app, g, make_response, render_template, request
from sqlalchemy.exc import SQLAlchemyError

from backend.identity.browser_handoffs import HandoffInvalid, redeem_browser_handoff
from backend.persistence.database import DatabaseUnavailable, session_scope
from backend.webapp.api_v1.context import begin_request
from backend.webapp.api_v1.responses import failure, success


browser_handoffs_bp = Blueprint("browser_handoffs", __name__)


@browser_handoffs_bp.before_request
def prepare_handoff_request():
    begin_request()


@browser_handoffs_bp.get("/access-handoff")
def access_handoff_page():
    response = make_response(render_template("access_handoff.html"))
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@browser_handoffs_bp.post("/api/browser-handoffs/redeem")
def redeem_handoff_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {"token"}:
        return failure("validation_failed", "The request body is invalid.", 400)
    token = payload.get("token")
    if not isinstance(token, str) or not 40 <= len(token) <= 512:
        return failure("handoff_invalid", "This Review Lab link is invalid or expired.", 401)
    try:
        with session_scope() as db_session:
            result = redeem_browser_handoff(
                db_session,
                raw_token=token,
                now=datetime.now(UTC),
                audit_writer=current_app.config["AUDIT_WRITER"],
                request_id=g.request_id,
            )
        response = success({"redeemed": True})
        response.set_cookie(
            "review_session",
            result.cookie_value,
            path="/",
            httponly=True,
            secure=True,
            samesite="Lax",
        )
        return response
    except HandoffInvalid:
        return failure("handoff_invalid", "This Review Lab link is invalid or expired.", 401)
    except (DatabaseUnavailable, SQLAlchemyError, RuntimeError):
        return failure(
            "dependency_unavailable",
            "Review Lab access is temporarily unavailable.",
            503,
            retryable=True,
        )
