"""Policy chat endpoint."""
import logging
import uuid
from flask import Blueprint, render_template, request, jsonify
from backend.pipeline.query import answer_question
from backend.webapp.api_v1.policy import (
    MAX_HISTORY_FIELD_CHARS,
    MAX_HISTORY_ITEMS,
    clean_policy_history,
)
from backend.webapp.errors import classify_error as _classify_error, ERROR_MESSAGES as _ERROR_MESSAGES

logger = logging.getLogger(__name__)
chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat")
def chat_page():
    return render_template("chat.html")


# Bounds on client-supplied history live with the shared cleaner in the v1
# policy module (RP-08). The browser and the Access client must bound history
# identically — two copies of these numbers is two things to drift.
_clean_history = clean_policy_history

__all__ = [
    "chat_bp", "MAX_HISTORY_ITEMS", "MAX_HISTORY_FIELD_CHARS", "_clean_history",
]


@chat_bp.route("/api/chat", methods=["POST"])
def chat_api():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "")
    if not question:
        return jsonify({"error": "No question provided"}), 400
    history = _clean_history(data.get("history"))

    try:
        result = answer_question(question, history=history)
        return jsonify(result)
    except Exception as exc:
        req_id = uuid.uuid4().hex[:8]
        category, status = _classify_error(exc)
        logger.exception("Chat query failed [category=%s, req_id=%s]", category, req_id)
        return jsonify({
            "error": _ERROR_MESSAGES[category],
            "request_id": req_id,
        }), status
