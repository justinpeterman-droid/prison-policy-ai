"""Policy chat endpoint."""
import logging
import uuid
from flask import Blueprint, render_template, request, jsonify
from backend.pipeline.query import answer_question
from backend.webapp.errors import classify_error as _classify_error, ERROR_MESSAGES as _ERROR_MESSAGES

logger = logging.getLogger(__name__)
chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat")
def chat_page():
    return render_template("chat.html")


# Bounds on client-supplied history. The browser is not trusted to be honest
# about size, and history goes straight into a prompt we pay per token for.
MAX_HISTORY_ITEMS = 6
MAX_HISTORY_FIELD_CHARS = 2000


def _clean_history(raw) -> list[dict]:
    """Coerce client-supplied history into bounded {question, answer} dicts.

    Anything malformed is dropped rather than rejected — a bad history should
    cost the officer conversational context, not their answer.
    """
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw[-MAX_HISTORY_ITEMS:]:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "")[:MAX_HISTORY_FIELD_CHARS]
        answer = str(item.get("answer") or "")[:MAX_HISTORY_FIELD_CHARS]
        if question.strip():
            out.append({"question": question, "answer": answer})
    return out


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
