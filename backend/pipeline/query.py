"""Search policy documents via Vertex AI Agent Builder (Discovery Engine).

Replaces old vertexai.preview.rag so search costs draw from the
$1,000 Vertex AI Agent Builder credit.

API contract unchanged: answer_question(question) -> {answer, citations, sources}
"""
import json
import logging
import re
import urllib.request
import urllib.error

import google.auth
import google.auth.transport.requests
from google import genai
from google.genai import types
from backend.pipeline.config import (
    PROJECT_ID, FAST_MODEL, PRO_MODEL, MODEL_LOCATION,
    AGENT_BUILDER_LOCATION, search_config_summary, serving_config_path,
)
from backend.pipeline.citations import build_grounded
from backend.pipeline.retry import with_retries
from backend.pipeline.retrieval import (
    augment_query, format_history, parse_search_results, select_passages,
)

logger = logging.getLogger(__name__)

# Retrieve broadly, but only feed the top passages to the generator (numbered +
# citable) — keeps the prompt focused and avoids "lost in the middle".
SEARCH_PAGE_SIZE = 25
MAX_CONTEXT_PASSAGES = 12
# Passages are now full extractive segments rather than clipped snippets, so
# count alone no longer bounds the prompt. Cap each passage, and the combined
# context, to keep the generator focused and the cost predictable.
MAX_PASSAGE_CHARS = 2000
MAX_CONTEXT_CHARS = 16000
# An officer waiting on a policy answer needs it to fail rather than hang.
ANSWER_TIMEOUT_MS = 90_000
# The gate is a one-word classification in front of every turn — it should fail
# fast and fall open rather than hold the request.
GATE_TIMEOUT_MS = 15_000
# A follow-up this short inside an existing conversation is taken as on-topic
# rather than judged standalone (see _classify_query).
FOLLOWUP_MAX_WORDS = 12

# Appended when the model answered without citing any retrieved passage — the
# grounding signal. Not suppressed (a DOMAIN_RULES safety answer may be
# passage-less), but clearly flagged so nobody treats it as document-backed.
UNGROUNDED_NOTE = (
    "\n\n⚠️ This answer could not be tied to a specific retrieved policy passage. "
    "Verify against the source policy or your supervisor before relying on it."
)

# Search + model config live in config.py.
#
# Note the two halves of the corpus setup: documents are INGESTED into the data
# store (AGENT_BUILDER_DATA_STORE, used by import_to_agent_builder.py), while
# SEARCH targets the ENGINE built on top of that store. This module declared a
# data-store id it never used in a request, which invited the assumption that
# search reads the store directly — it doesn't. If the engine is attached to a
# different data store than the one being imported into, ingestion succeeds and
# search still finds nothing.
LOCATION = AGENT_BUILDER_LOCATION
SERVING_CONFIG = serving_config_path()

_gen_client = None


def _get_gen_client() -> genai.Client:
    global _gen_client
    if _gen_client is None:
        _gen_client = genai.Client(vertexai=True, project=PROJECT_ID, location=MODEL_LOCATION)
    return _gen_client

# ── Domain Guard: hard-coded facts the AI must never contradict ──

DOMAIN_RULES = (
    "CRITICAL DOMAIN KNOWLEDGE — you MUST apply these rules:\n"
    "1. In a correctional facility, ANY personal relationship between staff "
    "and inmates beyond professional duties — including romantic, sexual, "
    "dating, or financial — is STRICTLY PROHIBITED under PREA (Prison Rape "
    "Elimination Act). There is NO gray area, NO exception, NO circumstance "
    "where this is allowed. The policy term is 'sexual misconduct' or "
    "'staff-on-offender sexual abuse.' This is a zero-tolerance policy.\n"
    "2. Treat informal officer language seriously: 'romantic'/'dating'/"
    "'messing around'/'hooking up' with an inmate = PREA sexual misconduct.\n"
    "3. If an officer asks about something that sounds minor (e.g. giving "
    "an inmate a ride, bringing them food, giving them money), this falls "
    "under undue familiarity / fraternization policies — also prohibited.\n"
    "4. NEVER say 'the documents don't explicitly say' when one of the above "
    "rules applies. State the prohibition clearly and cite PREA.\n"
)

CHAT_SYSTEM_PROMPT = (
    "You are a policy assistant for prison staff. Answer questions "
    "using ONLY the policy documents provided. Cite document numbers "
    "and sections. If the documents don't address the question, say so.\n\n"
    + DOMAIN_RULES
)

GATE_PROMPT = (
    "You are a gatekeeper for a prison policy reference tool. "
    "Classify this query as WORK or OFF_TOPIC.\n"
    "WORK = questions about prison policy, procedure, PREA, use of force, "
    "contraband, inmate management, disciplinary, training, security, "
    "emergencies, incident reports, forms, DOC regulations.\n"
    "OFF_TOPIC = personal questions, jokes, entertainment, general knowledge, "
    "coding, recipes, current events, politics, anything not about "
    "correctional facility operations.\n"
    "Output ONLY one word: WORK or OFF_TOPIC.\n\n"
    "Query: {question}\n"
    "Classification:"
)

# ── Gate keyword lists ──
#
# Split into strong and weak because the original single list matched bare
# substrings and accepted almost anything: "gate" fired inside "gateway",
# "report" accepted "write me a report about my dog", "count" accepted "how do
# I count cards at blackjack", "cell" accepted "my cell phone is broken". Every
# pattern is now word-bounded, and the generic words need corroboration.

_STRONG_WORK_TERMS = [
    # Corrections-specific: these words essentially don't occur off-topic.
    "prea", "use of force", "contraband", "inmate", "inmates", "offender",
    "post order", "disciplinary", "incident report", "005", "409",
    "barracks", "restraint", "restraints", "pat down", "shakedown",
    "visitation", "grievance", "restrictive housing", "segregation",
    "lockdown", "escape", "correctional", "prison", "warden",
    "department of correction", "adc", "bmc", "bmu", "ncu",
    "chain of command", "sally port", "commissary", "cell search",
    "strip search", "count time", "custody", "parole", "infirmary",
    "use-of-force", "shank", "cuff up", "dayroom",
]

# Generic on their own; a work signal when two or more appear together.
_WEAK_WORK_TERMS = [
    "policy", "procedure", "report", "form", "training", "cell", "search",
    "medical", "emergency", "security", "officer", "staff", "shift",
    "classification", "count", "gate", "tower", "rover", "supervisor",
    "sergeant", "lieutenant", "captain", "unit", "facility", "log",
]

_STRONG_WORK = [re.compile(rf"\b{re.escape(t)}\b") for t in _STRONG_WORK_TERMS]
_WEAK_WORK = [re.compile(rf"\b{re.escape(t)}\b") for t in _WEAK_WORK_TERMS]


def _http_error_hint(code: int) -> str:
    """Plain-language cause for the search failures that actually happen.

    These are all configuration problems that otherwise surface as an opaque
    5xx with no indication of which knob is wrong.
    """
    return {
        404: (f"the engine or serving config does not exist at this path — check "
              f"AGENT_BUILDER_ENGINE_ID (currently "
              f"{search_config_summary()['engine_id']!r}) and "
              f"AGENT_BUILDER_LOCATION (currently {LOCATION!r}); an engine "
              f"created in 'us' or 'eu' is not reachable at 'global'"),
        403: ("the service account lacks Discovery Engine permission on this "
              "project, or the Discovery Engine API is not enabled"),
        400: "the request body was rejected — likely an unsupported search spec field",
        401: "credentials were rejected — check Application Default Credentials",
    }.get(code, "")


def log_search_config() -> None:
    """Log the resolved search config once, so the active values are visible in
    logs without shell access to the container."""
    logger.info("Policy search config: %s", search_config_summary())


_token_cache = {"token": None, "expiry": 0}


def _get_token() -> str:
    """Get an OAuth token from Application Default Credentials."""
    import time
    if _token_cache["token"] and time.time() < _token_cache["expiry"] - 60:
        return _token_cache["token"]

    creds, project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    _token_cache["token"] = creds.token
    _token_cache["expiry"] = creds.expiry.timestamp() if creds.expiry else time.time() + 3500
    return creds.token


def _classify_query(question: str, history: list[dict] | None = None) -> bool:
    """Return True if this is a work-related query, False if off-topic.

    `history` matters: officers ask short follow-ups ("and if he refuses?",
    "how long do I have?") that carry no work vocabulary at all. Judged
    standalone those look like small talk, and the officer gets told they're
    at work in the middle of a policy conversation they are already having.
    A follow-up to an on-topic exchange is on-topic.
    """
    question_lower = question.lower().strip()

    # A short follow-up inside an existing policy conversation is on-topic by
    # construction — the gate already passed the turn it refers to.
    if history and len(question_lower.split()) <= FOLLOWUP_MAX_WORDS:
        logger.debug("Gate: short follow-up within an active conversation")
        return True

    # Fast keyword pre-check: obviously off-topic → reject immediately
    off_topic_patterns = [
        "write a poem", "tell me a joke", "recipe for", "how to cook",
        "weather today", "who won the", "sports score", "movie review",
        "stock price", "crypto", "bitcoin", "python code", "javascript",
        "write code", "debug this", "explain quantum", "who is the president",
        "what's your name", "how are you", "sing a song", "make me a",
        "generate a", "draw a", "translate to",
    ]
    for pat in off_topic_patterns:
        if pat in question_lower:
            logger.debug("Gate rejected by keyword match")
            return False

    # Unambiguous corrections vocabulary → accept immediately.
    if any(p.search(question_lower) for p in _STRONG_WORK):
        return True

    # Generic words that are only a work signal in context. One on its own means
    # nothing ("write me a report about my dog", "how do I count cards"); two or
    # more together is a real signal ("how do I report a medical emergency").
    if sum(1 for p in _WEAK_WORK if p.search(question_lower)) >= 2:
        return True

    # Ambiguous — use Gemini classifier
    try:
        response = _get_gen_client().models.generate_content(
            model=FAST_MODEL,
            contents=GATE_PROMPT.format(question=question),
            # The gate sits in front of every chat turn. Without a timeout a
            # hung call hangs the whole request with no bound — every other
            # Gemini call in this codebase sets one.
            config=types.GenerateContentConfig(
                http_options=types.HttpOptions(timeout=GATE_TIMEOUT_MS),
            ),
        )
        verdict = response.text.strip().upper()
        is_work = "WORK" in verdict and "OFF_TOPIC" not in verdict
        logger.info("Gate classified query as %s", "WORK" if is_work else "OFF_TOPIC")
        return is_work
    except Exception:
        logger.exception("Gate classification failed, allowing through")
        return True  # Fail open


def _search_body(query: str, page_size: int, rich: bool) -> dict:
    """Build the Discovery Engine search request.

    `rich` asks for extractive answers and segments in addition to snippets.
    Not every data store is provisioned for those, and asking for them where
    they aren't supported gets the whole request rejected — hence the ability
    to build the plain version.
    """
    content_spec: dict = {
        "snippetSpec": {"maxSnippetCount": 5, "returnSnippet": True},
    }
    if rich:
        content_spec["extractiveContentSpec"] = {
            "maxExtractiveAnswerCount": 3,
            "maxExtractiveSegmentCount": 3,
            # Pull in the text either side of a matched segment: policy
            # conditions and exceptions usually sit in the neighbouring
            # sentences, and a segment cut to the match alone reads as a rule
            # with no qualifiers.
            "numPreviousSegments": 1,
            "numNextSegments": 1,
        }
    return {
        "query": query,
        "pageSize": page_size,
        "queryExpansionSpec": {"condition": "AUTO"},
        "spellCorrectionSpec": {"mode": "AUTO"},
        "contentSearchSpec": content_spec,
    }


def _search_snippets_only(url: str, token: str, query: str, page_size: int,
                          original_error: str) -> dict:
    """Re-run the search without the extractive-content spec.

    If this also fails the data store is genuinely unreachable or
    misconfigured, so the original 400 is reported rather than this one — it
    describes the real problem.
    """
    data = json.dumps(_search_body(query, page_size, rich=False)).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Goog-User-Project", PROJECT_ID)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        logger.info("Snippets-only search returned %d results",
                    len(result.get("results", [])))
        return result
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:1000]
        logger.error("Search API error %s for serving config %s: %s",
                     e.code, SERVING_CONFIG, body)
        hint = _http_error_hint(e.code)
        if hint:
            logger.error("Likely cause: %s", hint)
        logger.error("The original request was also rejected (400): %s",
                     original_error[:300])
        raise RuntimeError(f"Search API error {e.code}")


def _search_data_store(query: str, page_size: int = 10) -> list[dict]:
    """Search the Agent Builder data store. Returns [{text, source}, ...]."""
    return _search_with_stats(query, page_size)[0]


def _search_with_stats(query: str, page_size: int = 10) -> tuple[list[dict], int]:
    """Search, returning (passages, raw_hit_count).

    The raw hit count lets the caller tell "nothing matched" apart from "hits
    matched but none carried readable text" — two failures that look identical
    from the passage list alone but mean very different things operationally.
    """
    token = _get_token()
    url = f"https://discoveryengine.googleapis.com/v1beta/{SERVING_CONFIG}:search"
    data = json.dumps(_search_body(query, page_size, rich=True)).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Goog-User-Project", PROJECT_ID)

    logger.info("Discovery Engine search: query=%r url=%s", query[:80], url)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            result = json.loads(raw)
            logger.info("Search returned %d results (totalSize=%s)",
                        len(result.get("results", [])),
                        result.get("totalSize", "?"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()[:1000]
        # A 400 means the request shape was rejected, and the only optional part
        # of it is the extractive-content spec — not every data store is
        # provisioned for extractive answers/segments. Falling back to snippets
        # keeps the chat working on those stores instead of failing every
        # search, which is exactly the single-point-of-failure this spec was
        # added to remove.
        if e.code == 400:
            logger.warning("Search rejected the extractive-content spec (400); "
                           "retrying with snippets only. Answers will be built "
                           "from shorter passages on this data store.")
            return _search_snippets_only(url, token, query, page_size, err_body)
        # Log the resolved config alongside the error: almost every other
        # failure here is a config mismatch, and the serving-config path is the
        # thing you need to see to spot it.
        logger.error("Search API error %s for serving config %s: %s",
                     e.code, SERVING_CONFIG, err_body)
        hint = _http_error_hint(e.code)
        if hint:
            logger.error("Likely cause: %s", hint)
        raise RuntimeError(f"Search API error {e.code}")
    except Exception as e:
        logger.error("Search failed against serving config %s: %s",
                     SERVING_CONFIG, e)
        raise

    raw_count = len(result.get("results", []) or [])
    contexts = parse_search_results(result, max_chars=MAX_PASSAGE_CHARS)
    # Raw-hit count vs. usable-passage count: when these diverge the search
    # worked but the text couldn't be read out of the response, which is a very
    # different problem from "nothing matched".
    if raw_count and not contexts:
        logger.error("Search returned %d result(s) but no passage text could be "
                     "extracted — check the data store's snippet/extractive "
                     "configuration", raw_count)
    elif raw_count != len(contexts):
        logger.info("Search: %d raw result(s) → %d usable passage(s)",
                    raw_count, len(contexts))
    return contexts, raw_count


def retrieve_context(question: str, top_k: int = 5) -> list[dict]:
    """Retrieve relevant policy chunks as {text, source} dicts."""
    return _search_data_store(question, top_k)


def answer_question(question: str, history: list[dict] | None = None) -> dict:
    """Full pipeline: gate → expand → search → generate.

    `history` is recent [{question, answer}] turns, used ONLY so the model can
    resolve follow-ups that are meaningless standalone ("and if he refuses?").
    The gate and retrieval stay per-turn, and the prompt is explicit that only
    the numbered passages are authoritative — a prior answer must never become
    a source of policy, or one bad answer would compound across a session.

    Returns {answer, citations, sources}:
      - citations: [{n, source, text}] full retrieved passages
      - sources: short labels for backward compat
    """
    # ── Gate check ──
    if not _classify_query(question, history):
        return {
            "answer": (
                "Good try — you're at work. If you believe this is wrong, "
                "contact Regional Three."
            ),
            "citations": [],
            "sources": [],
        }

    # ── Search ──
    # Augment (not replace) the question with formal terms for known slang; the
    # natural question still drives Discovery Engine's semantic understanding.
    retrieved, raw_count = _search_with_stats(augment_query(question),
                                              page_size=SEARCH_PAGE_SIZE)
    retrieved_sources = [c["source"] for c in retrieved]
    logger.info("answer_question: %d contexts, first source=%s",
                len(retrieved),
                retrieved[0]["source"][:60] if retrieved else "None")

    if not retrieved:
        # Matching documents but no readable text is a configuration problem,
        # not an empty corpus — don't tell the officer their question found
        # nothing when the search actually matched.
        answer = (
            "The policy search matched documents, but their text could not be "
            "read back. This is a system configuration issue, not a problem with "
            "your question — please report it and verify against the source "
            "policy in the meantime."
            if raw_count else
            "No relevant policy documents found for this question."
        )
        return {
            "answer": answer,
            "citations": [],
            "sources": [],
            "retrieved_sources": [],
        }

    # Trim to the top passages (dedupe + per-source cap), numbered for citation.
    contexts = select_passages(retrieved, MAX_CONTEXT_PASSAGES,
                               max_total_chars=MAX_CONTEXT_CHARS)
    numbered = "\n\n".join(
        f"[{i + 1}] (Source: {c['source']})\n{c['text']}"
        for i, c in enumerate(contexts)
    )
    # History is context for READING the question, never evidence for answering
    # it. Stated explicitly because prior answers can carry the ungrounded
    # warning or an error, and treating them as fact compounds the mistake.
    history_block = format_history(history)
    preamble = (
        f"EARLIER IN THIS CONVERSATION (context only — use it to understand what "
        f"the officer is referring to. It is NOT policy and NOT evidence; never "
        f"cite it):\n{history_block}\n\n"
        if history_block else ""
    )
    prompt = (
        f"{preamble}"
        f"POLICY PASSAGES (numbered):\n{numbered}\n\n"
        f"OFFICER'S QUESTION: {question}\n\n"
        "Answer using ONLY the numbered passages above. Immediately after each "
        "statement, cite the passage number(s) that support it in square brackets, "
        "e.g. '... must be reported within 24 hours [3].' Cite only passages that "
        "actually support the statement. If the officer used informal terms, map "
        "them to the formal policy language. If the passages do not answer the "
        "question, say so plainly."
    )

    def _call():
        return _get_gen_client().models.generate_content(
            model=PRO_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=CHAT_SYSTEM_PROMPT,
                http_options=types.HttpOptions(timeout=ANSWER_TIMEOUT_MS),
            ),
        )

    response = with_retries(_call, describe="chat answer generation")

    # Surface only the passages the model actually cited; flag ungrounded answers.
    # infer=True: if the model wrote a passage-derived answer but forgot the [n]
    # brackets, recover the citations by wording overlap rather than warning the
    # officer that a correct answer couldn't be tied to policy.
    answer, citations, grounded = build_grounded(response.text, contexts, infer=True)
    if not grounded:
        answer = (response.text or "").rstrip() + UNGROUNDED_NOTE
    logger.info("answer_question: grounded=%s, %d citation(s)", grounded, len(citations))

    return {
        "answer": answer,
        "citations": citations,
        "sources": [c["source"] for c in citations],
        "retrieved_sources": retrieved_sources,
    }
