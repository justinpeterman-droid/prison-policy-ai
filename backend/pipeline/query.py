"""Search policy documents via Vertex AI Agent Builder (Discovery Engine).

Replaces old vertexai.preview.rag so search costs draw from the
$1,000 Vertex AI Agent Builder credit.

API contract unchanged: answer_question(question) -> {answer, citations, sources}
"""
import os
import json
import logging
import urllib.request
import urllib.error

import google.auth
import google.auth.transport.requests
import vertexai
from vertexai.generative_models import GenerativeModel
from backend.pipeline.config import PROJECT_ID, GENERATION_MODEL

logger = logging.getLogger(__name__)

LOCATION = os.getenv("AGENT_BUILDER_LOCATION", "global")
DATA_STORE_ID = os.getenv("AGENT_BUILDER_DATA_STORE", "prison-policies-ds")
MODEL_LOCATION = os.getenv("GCP_MODEL_LOCATION", "global")

SERVING_CONFIG = (
    f"projects/{PROJECT_ID}/locations/{LOCATION}"
    f"/collections/default_collection/engines/prison-policies-engine"
    f"/servingConfigs/default_search"
)

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

QUERY_EXPANSION_PROMPT = (
    "You are helping a prison officer search policy documents. "
    "Rewrite their question into 3-5 search keywords. "
    "Officers use informal language — map it to formal policy terms:\n"
    "- 'romantic' / 'dating' / 'hooking up' / 'relationship' with inmate → PREA sexual misconduct staff inmate\n"
    "- 'fight' / 'beat down' → use of force\n"
    "- 'stuff' / 'things they shouldn't have' → contraband\n"
    "- 'walked off' / 'left' → escape walkaway\n"
    "- 'ride' / 'drive' / 'favor' for inmate → undue familiarity fraternization\n"
    "Output ONLY the keywords, no explanation.\n\n"
    "Question: {question}\n"
    "Keywords:"
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


def _classify_query(question: str) -> bool:
    """Return True if this is a work-related query, False if off-topic."""
    question_lower = question.lower().strip()

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
            logger.info("Gate rejected (keyword): %r", question[:80])
            return False

    # Obvious work terms → accept immediately
    work_patterns = [
        "prea", "use of force", "contraband", "inmate", "offender",
        "policy", "procedure", "post order", "shift", "disciplinary",
        "report", "form", "005", "training", "barracks", "cell",
        "restraint", "search", "pat down", "visitation", "grievance",
        "classification", "count", "lockdown", "segregation",
        "restrictive housing", "medical", "emergency", "escape",
        "security", "officer", "staff", "correctional", "prison",
        "doc ", "department of correction", "bmc", "bmu", "ncu",
        "chain of command", "gate", "tower", "rover", "sally port",
    ]
    for pat in work_patterns:
        if pat in question_lower:
            return True

    # Ambiguous — use Gemini classifier
    try:
        vertexai.init(project=PROJECT_ID, location=MODEL_LOCATION)
        model = GenerativeModel(GENERATION_MODEL)
        prompt = GATE_PROMPT.format(question=question)
        response = model.generate_content(prompt)
        verdict = response.text.strip().upper()
        is_work = "WORK" in verdict and "OFF_TOPIC" not in verdict
        logger.info("Gate classified: %r -> %s", question[:80], "WORK" if is_work else "OFF_TOPIC")
        return is_work
    except Exception:
        logger.exception("Gate classification failed, allowing through")
        return True  # Fail open


def _expand_query(question: str) -> str:
    """Rewrite colloquial officer language into policy search terms."""
    try:
        vertexai.init(project=PROJECT_ID, location=MODEL_LOCATION)
        model = GenerativeModel(GENERATION_MODEL)
        prompt = QUERY_EXPANSION_PROMPT.format(question=question)
        response = model.generate_content(prompt)
        expanded = response.text.strip().strip('"')
        if expanded and expanded != question:
            logger.info("Query expanded: %r -> %r", question[:80], expanded[:120])
            return expanded
    except Exception:
        logger.exception("Query expansion failed, using original query")
    return question


def _search_data_store(query: str, page_size: int = 5) -> list[dict]:
    """Search the Agent Builder data store. Returns [{text, source}, ...]."""
    token = _get_token()
    url = f"https://discoveryengine.googleapis.com/v1beta/{SERVING_CONFIG}:search"
    body = {
        "query": query,
        "pageSize": page_size,
        "queryExpansionSpec": {"condition": "AUTO"},
        "spellCorrectionSpec": {"mode": "AUTO"},
        "contentSearchSpec": {
            "snippetSpec": {"maxSnippetCount": 20, "returnSnippet": True},
            "extractiveContentSpec": {"maxExtractiveSegmentCount": 5},
        },
    }
    data = json.dumps(body).encode()
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
        logger.error("Search API error %s: %s", e.code, err_body)
        raise RuntimeError(f"Search API error {e.code}")
    except Exception as e:
        logger.error("Search failed: %s", e)
        raise

    contexts = []
    for r in result.get("results", []):
        doc = r.get("document", {}).get("derivedStructData", {})
        # Gather snippets
        snippets = doc.get("snippets", [])
        snippet_text = " ".join(s.get("snippet", "") for s in snippets)
        # Gather extractive segments (longer coherent passages)
        extractive_segments = doc.get("extractiveSegments", [])
        segment_text = " ".join(
            s.get("content", "") for s in extractive_segments
        )
        # Build text: prefer segments (longer) + supplement with snippets
        parts = []
        if segment_text:
            parts.append(segment_text)
        if snippet_text and snippet_text not in (parts[0] if parts else ""):
            parts.append(snippet_text)
        text = "\n\n".join(parts)
        if not text:
            extractive = doc.get("extractiveAnswers", [{}])
            text = extractive[0].get("content", "") if extractive else ""
        title = doc.get("title", "") or doc.get("structData", {}).get("title", "")
        if text:
            contexts.append({"text": text, "source": title or "Policy Document"})
    return contexts


def retrieve_context(question: str, top_k: int = 5) -> list[dict]:
    """Retrieve relevant policy chunks as {text, source} dicts."""
    return _search_data_store(question, top_k)


def answer_question(question: str) -> dict:
    """Full pipeline: gate → expand → search → generate.

    Returns {answer, citations, sources}:
      - citations: [{n, source, text}] full retrieved passages
      - sources: short labels for backward compat
    """
    # ── Gate check ──
    if not _classify_query(question):
        return {
            "answer": (
                "Good try — you're at work. If you believe this is wrong, "
                "contact Regional Three."
            ),
            "citations": [],
            "sources": [],
        }

    # ── Search ──
    contexts = _search_data_store(_expand_query(question), page_size=10)
    logger.info("answer_question: %d contexts, first source=%s",
                len(contexts),
                contexts[0]["source"][:60] if contexts else "None")

    if not contexts:
        return {
            "answer": "No relevant policy documents found for this question.",
            "citations": [],
            "sources": [],
        }

    context_text = "\n\n---\n\n".join(c["text"] for c in contexts)
    prompt = (
        f"POLICY DOCUMENTS:\n{context_text}\n\n"
        f"OFFICER'S QUESTION: {question}\n\n"
        f"Answer using the policy documents above. "
        f"If the officer used informal terms, map them to the formal policy language."
    )

    vertexai.init(project=PROJECT_ID, location=MODEL_LOCATION)
    model = GenerativeModel(
        model_name=GENERATION_MODEL,
        system_instruction=CHAT_SYSTEM_PROMPT,
    )
    response = model.generate_content(prompt)

    citations = [
        {"n": i + 1, "source": c["source"], "text": c["text"]}
        for i, c in enumerate(contexts)
    ]
    return {
        "answer": response.text,
        "citations": citations,
        "sources": [
            (c["source"] or c["text"][:80] + "...") for c in contexts
        ],
    }
