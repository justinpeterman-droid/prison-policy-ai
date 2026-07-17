"""Policy chat endpoint."""
import logging
from flask import Blueprint, render_template, request, jsonify
from backend.pipeline.query import answer_question

logger = logging.getLogger(__name__)
chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat")
def chat_page():
    return render_template("chat.html")


@chat_bp.route("/api/chat", methods=["POST"])
def chat_api():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "")
    if not question:
        return jsonify({"error": "No question provided"}), 400

    try:
        result = answer_question(question)
        return jsonify(result)
    except Exception:
        logger.exception("Chat query failed")
        return jsonify({"error": "Query failed. Please try again."}), 500
