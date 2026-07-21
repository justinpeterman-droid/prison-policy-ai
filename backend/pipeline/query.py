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

CHAT_SYSTEM_PROMPT = (
    "You are a policy assistant. Answer questions using ONLY the policy "
    "documents provided. Cite document sections. If the answer is not in "
    "the documents, say so."
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


def _search_data_store(query: str, page_size: int = 5) -> list[dict]:
    """Search the Agent Builder data store. Returns [{text, source}, ...]."""
    token = _get_token()
    url = f"https://discoveryengine.googleapis.com/v1beta/{SERVING_CONFIG}:search"
    body = {
        "query": query,
        "pageSize": page_size,
        "queryExpansionSpec": {"condition": "AUTO"},
        "spellCorrectionSpec": {"mode": "AUTO"},
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Goog-User-Project", PROJECT_ID)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()[:1000]
        logger.error("Search API error %s: %s", e.code, err_body)
        raise RuntimeError(f"Search API error {e.code}")

    contexts = []
    for r in result.get("results", []):
        doc = r.get("document", {}).get("derivedStructData", {})
        snippets = doc.get("snippets", [])
        text = " ".join(s.get("snippet", "") for s in snippets)
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
    """Full pipeline: search Agent Builder -> generate with Gemini.

    Returns {answer, citations, sources}:
      - citations: [{n, source, text}] full retrieved passages
      - sources: short labels for backward compat
    """
    contexts = _search_data_store(question)

    if not contexts:
        return {
            "answer": "No relevant policy documents found for this question.",
            "citations": [],
            "sources": [],
        }

    context_text = "\n\n---\n\n".join(c["text"] for c in contexts)
    prompt = f"POLICY DOCUMENTS:\n{context_text}\n\nQUESTION: {question}"

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
