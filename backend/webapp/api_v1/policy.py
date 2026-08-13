"""Policy Expert `/api/v1` contract (RP-08).

This is the one `/api/v1` surface whose *request* is as sensitive as its
response. Officers quote live incidents into a question, and the answer quotes
policy back with citation passages. So the rule here is stricter than
"don't log the response": the question, the answer, the history and every
citation passage are deliberately never written to Cloud SQL, the audit trail,
or an ordinary log line. What survives a request is a SHA-256 of the question,
a document count, a latency figure and a result — enough to debug and bill,
never enough to reconstruct what was asked.

That deliberate non-persistence is what shapes the idempotency contract. ID-06
normally lets a duplicate key replay the first response; here there is no
stored response to replay, and re-calling the provider would silently double
the cost of an officer's fat-fingered retry. So a duplicate key is answered
honestly — `request_in_progress` while the first call is still running,
`idempotent_response_unavailable` once it has settled — and an officer who
genuinely wants to ask again does so with a new key, as an explicit act.

The claim is committed *before* the provider call. That ordering is the whole
mechanism: an uncommitted claim is invisible to a concurrent duplicate, which
would then buy a second provider request for the same key.
"""

from datetime import UTC, datetime
import hashlib
from time import monotonic

from flask import Blueprint, current_app, g, request

from backend.identity.audit import AuditEventInput
from backend.identity.idempotency import (
    IdempotencyConflict,
    RequestInProgress,
    claim_idempotency,
    complete_idempotency,
    request_digest,
)
from backend.persistence.models.security import IdempotencyRecord
from backend.pipeline.query import answer_question
from backend.persistence.database import DatabaseUnavailable, session_scope
from backend.webapp.api_v1.client_policy import require_compatible_write
from backend.webapp.api_v1.context import REQUEST_ID_PATTERN, request_id
from backend.webapp.api_v1.errors import ApiError
from backend.webapp.api_v1.middleware import (
    current_actor,
    current_request_session,
    require_access_token,
)
from backend.webapp.api_v1.responses import success
from backend.webapp.errors import classify_error
from sqlalchemy.exc import SQLAlchemyError


policy_bp = Blueprint("policy_api", __name__)

# Bounds on client-supplied history. Shared verbatim with the browser chat
# route — a second copy of these numbers is a second thing to drift.
MAX_HISTORY_ITEMS = 6
MAX_HISTORY_FIELD_CHARS = 2000

MAX_QUESTION_CHARS = 4000
MAX_SOURCE_CHARS = 300
MAX_CITATION_TEXT_CHARS = 8000

# The server's own budget. The Access client waits on this synchronously, so an
# unbounded provider call would hold a worker and a user hostage indefinitely.
POLICY_BUDGET_SECONDS = 90.0

IDEMPOTENCY_ACTION = "policy_question"

_ALLOWED_REQUEST_FIELDS = frozenset({"question", "history"})
_ALLOWED_TURN_FIELDS = frozenset({"question", "answer"})

# classify_error() speaks in operational categories; `/api/v1` speaks in stable
# client-facing codes. Nothing upstream-specific may cross this boundary.
_ERROR_TRANSLATION = {
    "credentials": ("dependency_unavailable", 503, False),
    "model": ("dependency_unavailable", 503, False),
    "permission": ("dependency_unavailable", 503, False),
    "upstream": ("dependency_unavailable", 503, True),
    "quota": ("dependency_unavailable", 503, True),
    "timeout": ("dependency_timeout", 504, True),
    "internal": ("internal_error", 500, False),
}
_SAFE_ERROR_MESSAGES = {
    "dependency_unavailable": "The Policy Expert is temporarily unavailable. Try again shortly.",
    "dependency_timeout": "The Policy Expert took too long to answer. Try a shorter, more specific question.",
    "internal_error": "An unexpected error occurred.",
}


def clean_policy_history(raw) -> list[dict[str, str]]:
    """Coerce client-supplied history into bounded {question, answer} pairs.

    Anything malformed is dropped rather than rejected — a bad history should
    cost the officer conversational context, not their answer.
    """
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw[-MAX_HISTORY_ITEMS:]:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "")[:MAX_HISTORY_FIELD_CHARS]
        answer = str(item.get("answer") or "")[:MAX_HISTORY_FIELD_CHARS]
        if question.strip():
            out.append({"question": question, "answer": answer})
    return out


def _invalid(message: str = "The policy question request is invalid.") -> ApiError:
    return ApiError("validation_failed", message, status=400)


def _parse_request() -> tuple[str, list[dict[str, str]]]:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise _invalid()
    if not set(body) <= _ALLOWED_REQUEST_FIELDS:
        raise _invalid()
    question = body.get("question")
    if not isinstance(question, str) or not question.strip():
        raise _invalid()
    if len(question) > MAX_QUESTION_CHARS:
        raise _invalid()
    raw_history = body.get("history")
    if raw_history is not None and not isinstance(raw_history, list):
        raise _invalid()
    for turn in raw_history or []:
        if isinstance(turn, dict) and not set(turn) <= _ALLOWED_TURN_FIELDS:
            raise _invalid()
    return question.strip(), clean_policy_history(raw_history)


def _idempotency_key() -> str:
    key = request.headers.get("Idempotency-Key", "")
    if not key:
        raise _invalid("Idempotency-Key is required.")
    return key


def _require_request_id() -> None:
    """Require an auditable caller-supplied identifier on paid API work."""
    if not REQUEST_ID_PATTERN.fullmatch(request.headers.get("X-Request-ID", "")):
        raise _invalid("X-Request-ID is required and must be valid.")


def _latency_bucket(latency_ms: int) -> str:
    if latency_ms < 1_000:
        return "under_1s"
    if latency_ms < 5_000:
        return "1_to_5s"
    if latency_ms < 30_000:
        return "5_to_30s"
    return "30s_or_more"


def _call_provider(question: str, history: list[dict[str, str]]) -> dict:
    """Run the pipeline synchronously with one end-to-end deadline.

    The shared pipeline applies it to its gate, Discovery Engine, and model
    calls, so a 504 does not abandon a provider call running in a thread.
    """
    return answer_question(
        question,
        history=history,
        deadline_monotonic=monotonic() + POLICY_BUDGET_SECONDS,
    )


def _rollback_quietly(db) -> None:
    try:
        db.rollback()
    except SQLAlchemyError:
        pass


def _settle_failure_after_persistence_error(claim, *, latency_ms: int) -> None:
    """Settle a committed claim from a fresh session after a broken connection."""
    with session_scope() as recovery:
        record = recovery.get(IdempotencyRecord, claim.record_id, with_for_update=True)
        if record is None or record.status != "in_progress":
            return
        complete_idempotency(
            recovery,
            claim,
            response_status=503,
            response_reference={
                "result": "error",
                "latency_bucket": _latency_bucket(latency_ms),
            },
            now=datetime.now(UTC),
        )


def _bounded_string(value: object, limit: int) -> str:
    return value[:limit] if isinstance(value, str) else ""


def _policy_data(result: object) -> dict[str, object]:
    """Project untrusted pipeline output into the closed Access wire schema."""
    raw = result if isinstance(result, dict) else {}
    citations: list[dict[str, object]] = []
    for item in raw.get("citations") or []:
        if not isinstance(item, dict):
            continue
        number = item.get("n")
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            continue
        source = _bounded_string(item.get("source"), MAX_SOURCE_CHARS)
        text = _bounded_string(item.get("text"), MAX_CITATION_TEXT_CHARS)
        if source and text:
            citations.append({"n": number, "source": source, "text": text})

    def source_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [
            text for item in value if (text := _bounded_string(item, MAX_SOURCE_CHARS))
        ]

    return {
        "answer": _bounded_string(raw.get("answer"), MAX_QUESTION_CHARS * 4),
        "citations": citations,
        "sources": source_list(raw.get("sources")),
        "retrieved_sources": source_list(raw.get("retrieved_sources")),
    }


def _settle(db, claim, *, status: int, reference: dict[str, object], now) -> None:
    """Close out the idempotency claim and commit, so the key never strands.

    Committed on the failure path too: an `in_progress` row left behind by a
    crashed call would lock that key out until it expired, and the officer would
    have no way to tell that from a real duplicate.
    """
    complete_idempotency(
        db,
        claim,
        response_status=status,
        response_reference=reference,
        now=now,
    )
    db.commit()


@policy_bp.post("/questions", endpoint="ask")
@require_access_token
@require_compatible_write
def ask_policy_question():
    _require_request_id()
    key = _idempotency_key()
    question, history = _parse_request()
    db = current_request_session()
    actor = current_actor()
    now = datetime.now(UTC)

    digest = request_digest({"question": question, "history": history})
    try:
        claim = claim_idempotency(
            db,
            actor,
            key=key,
            action=IDEMPOTENCY_ACTION,
            request_sha256=digest,
            now=now,
        )
    except RequestInProgress:
        _rollback_quietly(db)
        raise ApiError(
            "request_in_progress",
            "That question is still being answered. Wait for the first answer.",
            status=409,
            retryable=True,
        ) from None
    except IdempotencyConflict:
        _rollback_quietly(db)
        raise ApiError(
            "idempotency_conflict",
            "That Idempotency-Key was already used for a different question.",
            status=409,
        ) from None
    except ValueError:
        _rollback_quietly(db)
        raise _invalid("Idempotency-Key is invalid.") from None
    except (DatabaseUnavailable, SQLAlchemyError):
        _rollback_quietly(db)
        raise ApiError(
            "dependency_unavailable",
            "The Policy Expert is temporarily unavailable. Try again shortly.",
            status=503,
            retryable=True,
        ) from None

    if claim.replayed:
        # By design there is nothing to replay: the answer was never stored.
        _rollback_quietly(db)
        raise ApiError(
            "idempotent_response_unavailable",
            "That question was already answered. Policy answers are not stored, "
            "so ask again with a new Idempotency-Key to receive a fresh answer.",
            status=409,
        )

    # Commit the claim before the provider call so a concurrent duplicate can
    # see it and be refused instead of buying a second provider request.
    try:
        db.commit()
    except (DatabaseUnavailable, SQLAlchemyError):
        _rollback_quietly(db)
        raise ApiError(
            "dependency_unavailable",
            "The Policy Expert is temporarily unavailable. Try again shortly.",
            status=503,
            retryable=True,
        ) from None

    started = monotonic()
    try:
        result = _call_provider(question, history)
    except Exception as exc:  # noqa: BLE001 - every failure is translated below
        category, _status = classify_error(exc)
        code, http_status, retryable = _ERROR_TRANSLATION.get(
            category, ("internal_error", 500, False)
        )
        latency_ms = max(0, int((monotonic() - started) * 1000))
        try:
            _settle(
                db,
                claim,
                status=http_status,
                reference={
                    "result": "error",
                    "latency_bucket": _latency_bucket(latency_ms),
                },
                now=datetime.now(UTC),
            )
        except (DatabaseUnavailable, SQLAlchemyError):
            _rollback_quietly(db)
            try:
                _settle_failure_after_persistence_error(claim, latency_ms=latency_ms)
            except (DatabaseUnavailable, SQLAlchemyError):
                pass
            raise ApiError(
                "dependency_unavailable",
                "The Policy Expert is temporarily unavailable. Try again shortly.",
                status=503,
                retryable=True,
            ) from None
        g.api_dependency = "policy_expert"
        raise ApiError(
            code,
            _SAFE_ERROR_MESSAGES[code],
            status=http_status,
            retryable=retryable,
        ) from None

    latency_ms = max(0, int((monotonic() - started) * 1000))
    data = _policy_data(result)
    answer = data["answer"]
    citations = data["citations"]

    settled_at = datetime.now(UTC)
    try:
        current_app.config["AUDIT_WRITER"].append(
            db,
            AuditEventInput(
                actor_account_id=actor.account_id,
                actor_staff_member_id=actor.staff_member_id,
                action="policy.question_answered",
                result="success",
                request_id=request_id(),
                target_type="policy_question",
                target_id=None,
                details={
                    "document_count": len(citations),
                    "latency_ms": min(latency_ms, 1_000_000_000),
                },
                client_version=str(g.client_version),
            ),
        )
        _settle(
            db,
            claim,
            status=200,
            reference={
                "result": "success",
                "latency_bucket": _latency_bucket(latency_ms),
                "response_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
                "citation_count": len(citations),
            },
            now=settled_at,
        )
    except (DatabaseUnavailable, SQLAlchemyError):
        _rollback_quietly(db)
        try:
            _settle_failure_after_persistence_error(claim, latency_ms=latency_ms)
        except (DatabaseUnavailable, SQLAlchemyError):
            pass
        raise ApiError(
            "dependency_unavailable",
            "The Policy Expert is temporarily unavailable. Try again shortly.",
            status=503,
            retryable=True,
        ) from None
    g.api_dependency = "policy_expert"
    return success(data)
