"""Semantic reranking for the policy chat (Vertex AI Ranking API).

Discovery Engine hands back its hits in *retrieval* order — scored with the
question and each document read separately, and tuned for recall: get the right
document somewhere into the top 25. Deciding which of those 25 passages
actually answers the officer's question is a harder judgement, and the
retriever never makes it.

The Ranking API is a cross-encoder: it reads the question and one passage
*together* and scores that pair. Too slow to run over a corpus, exactly right
over the handful of passages retrieval already found.

Why the ordering matters so much downstream: `select_passages` applies its
per-source cap and character budget in list order, and only the first
MAX_CONTEXT_PASSAGES ever reach the generator. Everything after retrieval
inherits the retriever's ranking, so a passage that is squarely on point but
sits 14th is not merely ranked low — it is never seen. Reranking first spends
those budgets on the best passages rather than the earliest ones.

**This module fails open, always.** A ranking outage, a missing permission, a
slow response, a malformed reply — none of them is a reason to fail an
officer's policy question. Every failure path returns the passages exactly as
they arrived and logs the reason. The chat is never worse off than it was
before this module existed; at worst it is unchanged.

The pure parts (`build_records`, `reorder`) carry the ordering contract and are
unit-tested without GCP; only `rerank_passages` touches the network.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from backend.pipeline.config import (
    PROJECT_ID, RERANK_ENABLED, RERANK_MODEL, ranking_config_path,
)
from backend.pipeline.gcp_auth import get_access_token

logger = logging.getLogger(__name__)

# Ranking API limits: at most 200 records per request, and the model reads
# roughly the first 512 tokens of each record. Search only ever hands us
# SEARCH_PAGE_SIZE (25), so the record cap is a guard rather than a live
# constraint; the char caps keep each record inside what the ranker will
# actually read.
MAX_RECORDS = 200
MAX_RECORD_CHARS = 2000
MAX_QUERY_CHARS = 1000
# The reranker is an optimisation on a request an officer is already waiting
# on. It gets a short leash — past this it is faster to answer from the
# retriever's order than to keep waiting for a better one.
TIMEOUT_S = 10

RANK_ENDPOINT = "https://discoveryengine.googleapis.com/v1/{config}:rank"

# HTTP statuses where retrying, or even trying again next turn, cannot help:
# the ranking config doesn't exist, the API isn't enabled, the service account
# lacks the permission, or the request shape is rejected. These are deployment
# facts, not weather. Rather than pay the latency on every single chat turn
# forever, the first one switches the reranker off for the life of the process
# and says so once.
_PERMANENT_STATUSES = (400, 401, 403, 404)

_state: dict = {"disabled_reason": None}


class _PermanentRerankError(RuntimeError):
    """A failure that will repeat identically on every subsequent request."""


def rerank_status() -> dict:
    """Current reranker state, for logs and `scripts/check_search.py`."""
    return {
        "enabled": RERANK_ENABLED,
        "model": RERANK_MODEL,
        "ranking_config": ranking_config_path(),
        "disabled_reason": _state["disabled_reason"],
    }


def reset_rerank_state() -> None:
    """Clear the process-level disable. For tests."""
    _state["disabled_reason"] = None


def _disable(reason: str) -> None:
    if _state["disabled_reason"] is None:
        _state["disabled_reason"] = reason
        logger.warning(
            "Semantic reranking disabled for this process: %s. Policy chat "
            "continues on the retriever's own ordering — answers are unaffected, "
            "passage ordering is just not improved. Ranking config: %s",
            reason, ranking_config_path())


def build_records(passages: list[dict], max_records: int = MAX_RECORDS,
                  max_chars: int = MAX_RECORD_CHARS) -> list[dict]:
    """Turn `[{text, source}]` into Ranking API records.

    The record id is the passage's index in the ORIGINAL list, as a string —
    that is what makes the response mappable back onto the caller's passages
    without matching on text. Passages with no text are skipped rather than
    sent as empty records; they carry nothing for the ranker to score, and
    `select_passages` drops them downstream anyway.
    """
    records: list[dict] = []
    for i, p in enumerate(passages or []):
        if len(records) >= max_records:
            break
        text = (p.get("text") or "").strip()
        if not text:
            continue
        records.append({
            "id": str(i),
            "title": (p.get("source") or "")[:200],
            "content": text[:max_chars],
        })
    return records


def reorder(passages: list[dict], ranked_ids: list[str]) -> list[dict]:
    """Reorder `passages` to follow `ranked_ids`, keeping every passage.

    Anything the response didn't mention — records the ranker dropped, passages
    that were never sent, ids that don't parse — keeps its original relative
    order at the end of the list. Reranking is allowed to change what is
    *first*; it is not allowed to lose a passage. A truncated or partial
    response would otherwise silently shrink the evidence the generator sees,
    which is the one failure mode that would make this module worse than not
    having it.
    """
    ranked: list[dict] = []
    used: set[int] = set()
    for rid in ranked_ids or []:
        try:
            idx = int(rid)
        except (TypeError, ValueError):
            continue
        if idx in used or not 0 <= idx < len(passages):
            continue
        used.add(idx)
        ranked.append(passages[idx])
    ranked.extend(p for i, p in enumerate(passages) if i not in used)
    return ranked


def _parse_ranked_ids(payload: dict) -> list[str]:
    """Pull the ranked record ids out of a RankResponse, best order first."""
    out: list[str] = []
    for record in (payload or {}).get("records", []) or []:
        if not isinstance(record, dict):
            continue
        rid = record.get("id")
        if isinstance(rid, (str, int)):
            out.append(str(rid))
    return out


def _rank(question: str, records: list[dict], token: str) -> list[str]:
    """One Ranking API call. Returns ranked record ids, best first."""
    url = RANK_ENDPOINT.format(config=ranking_config_path())
    body = {
        "model": RERANK_MODEL,
        "query": question[:MAX_QUERY_CHARS],
        "records": records,
        # Ask for the full set back: this is a reordering pass, and trimming is
        # select_passages' job — it still has a per-source cap and a character
        # budget to apply, and it needs the whole list to apply them to.
        "topN": len(records),
        # Scores and ids are all that's used; echoing every passage back
        # doubles the response for nothing.
        "ignoreRecordDetailsInResponse": True,
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Goog-User-Project", PROJECT_ID)

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as http_exc:
        detail = ""
        try:
            detail = http_exc.read().decode()[:300]
        except Exception:  # noqa: BLE001  pylint: disable=broad-exception-caught
            # Best-effort context only. The status code is what decides
            # behaviour, and failing to read the body must not replace a
            # handled ranking failure with an unhandled one.
            pass
        if http_exc.code in _PERMANENT_STATUSES:
            raise _PermanentRerankError(
                f"HTTP {http_exc.code} from the Ranking API: {detail}") from http_exc
        raise RuntimeError(f"HTTP {http_exc.code}: {detail}") from http_exc
    return _parse_ranked_ids(payload)


def rerank_passages(question: str, passages: list[dict], *,
                    token_provider=None) -> list[dict]:
    """Reorder retrieved passages by cross-encoder relevance to `question`.

    Returns the passages unchanged — never fewer, never an exception — if
    reranking is off, unavailable, or fails for any reason.

    Pass the officer's ORIGINAL question, not the slang-augmented search query.
    The appended policy terms exist to widen lexical recall in Discovery
    Engine; the ranker scores the question against each passage semantically,
    and a tail of injected keywords just dilutes the sentence it is meant to be
    reading.

    `token_provider` is resolved here rather than defaulted in the signature, so
    that patching `get_access_token` on this module actually takes effect — a
    default argument would have bound the original at import time.
    """
    # Switched off, already known unavailable, or nothing to reorder — none of
    # these should spend a round-trip proving it.
    if (not RERANK_ENABLED or _state["disabled_reason"]
            or len(passages or []) < 2 or not (question or "").strip()):
        return passages

    records = build_records(passages)
    if len(records) < 2:
        return passages

    try:
        ranked_ids = _rank(question, records, (token_provider or get_access_token)())
    except _PermanentRerankError as exc:
        _disable(str(exc))
        return passages
    except Exception as exc:  # noqa: BLE001  pylint: disable=broad-exception-caught
        # Deliberately unconditional: this module's contract is that NO ranking
        # failure can cost an officer their answer. Narrowing this to the
        # exceptions we currently expect means the next unexpected one — a new
        # SDK error class, a malformed body, a JSON decode failure — takes the
        # chat down for a passage-ordering optimisation.
        logger.warning("Semantic reranking failed (%s: %s); using the "
                       "retriever's ordering for this question.",
                       type(exc).__name__, exc)
        return passages

    if not ranked_ids:
        logger.warning("Ranking API returned no records for %d passage(s); "
                       "using the retriever's ordering.", len(records))
        return passages

    out = reorder(passages, ranked_ids)
    if out and passages and out[0] is not passages[0]:
        # The signal worth watching when judging whether this lever pays for
        # itself: how often the ranker disagrees with the retriever about which
        # passage matters most.
        logger.info("Reranked %d passage(s): top source %r → %r",
                    len(records), passages[0].get("source"), out[0].get("source"))
    else:
        logger.debug("Reranked %d passage(s); top passage unchanged", len(records))
    return out
