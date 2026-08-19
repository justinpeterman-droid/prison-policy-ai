"""Cookie-authenticated Policy Expert route for Guided Operations.

Questions, answers, and citation passages are deliberately transient. Only
bounded control metadata is persisted for idempotency and audit attribution.
"""
from datetime import UTC, datetime
import hashlib
from time import monotonic

from flask import Blueprint, current_app, g, request
from sqlalchemy.exc import SQLAlchemyError

from backend.identity.audit import AuditEventInput
from backend.identity.idempotency import (
    IdempotencyConflict,
    RequestInProgress,
    claim_idempotency,
    complete_idempotency,
    request_digest,
)
from backend.persistence.database import DatabaseUnavailable
from backend.pipeline.query import answer_question
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.responses import success
from backend.webapp.errors import classify_error
from backend.webapp.web_api.middleware import (
    current_browser_actor,
    current_browser_session,
    require_browser_csrf,
    require_browser_session,
)


policy_bp = Blueprint("web_policy", __name__)
_MAX_QUESTION_CHARACTERS = 2_000
_POLICY_BUDGET_SECONDS = 90.0
_ERROR_TRANSLATION = {
    "credentials": ("dependency_unavailable", 503, False),
    "model": ("dependency_unavailable", 503, False),
    "permission": ("dependency_unavailable", 503, False),
    "upstream": ("dependency_unavailable", 503, True),
    "quota": ("dependency_unavailable", 503, True),
    "timeout": ("dependency_timeout", 504, True),
    "internal": ("internal_error", 500, False),
}
_SAFE_MESSAGES = {
    "dependency_unavailable": "The Policy Expert is temporarily unavailable. Try again shortly.",
    "dependency_timeout": "The Policy Expert took too long to answer. Try a shorter, more specific question.",
    "internal_error": "The Policy Expert could not complete the question.",
}


def _question() -> str:
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or set(body) != {"question"}:
        raise ApiError(
            "validation_failed",
            "The policy question request is invalid.",
            status=400,
        )
    value = body.get("question")
    if not isinstance(value, str):
        raise ApiError(
            "validation_failed",
            "Enter a policy question.",
            status=400,
        )
    cleaned = value.strip()
    if not cleaned or len(cleaned) > _MAX_QUESTION_CHARACTERS:
        raise ApiError(
            "validation_failed",
            "Policy questions must contain 1 through 2,000 characters.",
            status=400,
        )
    return cleaned


def _bounded(value: object, maximum: int) -> str:
    return value[:maximum] if isinstance(value, str) else ""


def _project_result(value: object) -> dict[str, object]:
    raw = value if isinstance(value, dict) else {}
    answer = _bounded(raw.get("answer"), 8_000).strip()
    citations: list[dict[str, object]] = []
    for item in raw.get("citations") or []:
        if not isinstance(item, dict):
            continue
        source = _bounded(item.get("source"), 300).strip()
        excerpt = _bounded(item.get("text"), 8_000).strip()
        number = item.get("n")
        if not source or not excerpt:
            continue
        citation: dict[str, object] = {
            "title": source,
            "excerpt": excerpt,
        }
        if isinstance(number, int) and not isinstance(number, bool) and number > 0:
            citation["location"] = f"Source passage {number}"
        citations.append(citation)
    if not answer:
        raise ApiError(
            "dependency_unavailable",
            "The Policy Expert returned an unreadable answer. Try again.",
            status=503,
            retryable=True,
        )
    if not citations:
        raise ApiError(
            "policy_sources_unavailable",
            answer,
            status=422,
            retryable=False,
        )
    return {"answer": answer, "citations": citations}


def _rollback(db) -> None:
    try:
        db.rollback()
    except SQLAlchemyError:
        pass


@policy_bp.post("/questions", endpoint="ask")
@require_browser_session
@require_browser_csrf
def ask_policy_question():
    question = _question()
    db = current_browser_session()
    actor = current_browser_actor()
    request_reference = str(g.get("request_id", ""))
    now = datetime.now(UTC)

    try:
        claim = claim_idempotency(
            db,
            actor,
            key=request_reference,
            action="browser.policy_question",
            request_sha256=request_digest({"question": question}),
            now=now,
        )
    except RequestInProgress:
        _rollback(db)
        raise ApiError(
            "request_in_progress",
            "That policy question is still being answered.",
            status=409,
            retryable=True,
        ) from None
    except IdempotencyConflict:
        _rollback(db)
        raise ApiError(
            "idempotency_conflict",
            "The request identifier was already used.",
            status=409,
        ) from None
    except ValueError:
        _rollback(db)
        raise ApiError("validation_failed", "The request identifier is invalid.", status=400) from None
    except (DatabaseUnavailable, SQLAlchemyError):
        _rollback(db)
        raise ApiError(
            "dependency_unavailable",
            _SAFE_MESSAGES["dependency_unavailable"],
            status=503,
            retryable=True,
        ) from None

    if claim.replayed:
        _rollback(db)
        raise ApiError(
            "idempotent_response_unavailable",
            "That question was already answered. Ask again to receive a fresh answer.",
            status=409,
        )

    # Make the in-progress claim visible before the paid provider request.
    try:
        db.commit()
    except (DatabaseUnavailable, SQLAlchemyError):
        _rollback(db)
        raise ApiError(
            "dependency_unavailable",
            _SAFE_MESSAGES["dependency_unavailable"],
            status=503,
            retryable=True,
        ) from None

    started = monotonic()
    try:
        projected = _project_result(answer_question(
            question,
            history=None,
            deadline_monotonic=monotonic() + _POLICY_BUDGET_SECONDS,
        ))
    except ApiError:
        raise
    except Exception as error:  # noqa: BLE001 - translated to stable public codes
        category, _status = classify_error(error)
        code, status, retryable = _ERROR_TRANSLATION.get(
            category,
            ("internal_error", 500, False),
        )
        raise ApiError(
            code,
            _SAFE_MESSAGES[code],
            status=status,
            retryable=retryable,
        ) from None

    latency_ms = max(0, int((monotonic() - started) * 1_000))
    try:
        current_app.config["AUDIT_WRITER"].append(db, AuditEventInput(
            actor_account_id=actor.account_id,
            actor_staff_member_id=actor.staff_member_id,
            action="policy.question_answered",
            result="success",
            request_id=request_reference,
            target_type="policy_question",
            target_id=None,
            details={
                "document_count": len(projected["citations"]),
                "latency_ms": min(latency_ms, 1_000_000_000),
            },
            client_version=str(g.get("client_version", "")),
        ))
        complete_idempotency(
            db,
            claim,
            response_status=200,
            response_reference={
                "result": "success",
                "response_sha256": hashlib.sha256(
                    str(projected["answer"]).encode("utf-8")
                ).hexdigest(),
                "citation_count": len(projected["citations"]),
            },
            now=datetime.now(UTC),
        )
        db.flush()
    except (DatabaseUnavailable, SQLAlchemyError, KeyError, RuntimeError):
        _rollback(db)
        raise ApiError(
            "dependency_unavailable",
            _SAFE_MESSAGES["dependency_unavailable"],
            status=503,
            retryable=True,
        ) from None

    return success(projected)
