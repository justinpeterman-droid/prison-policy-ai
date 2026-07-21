"""Search policy documents via Vertex AI Agent Builder (Discovery Engine).

Replaces the old vertexai.preview.rag path so that search costs draw
from the $1,000 Vertex AI Agent Builder credit.

API contract unchanged: answer_question(question) -> {answer, citations, sources}
"""
import os
import json
import urllib.request
import urllib.error
import subprocess

import vertexai
from vertexai.generative_models import GenerativeModel
from backend.pipeline.config import PROJECT_ID, GENERATION_MODEL

LOCATION = os.getenv("AGENT_BUILDER_LOCATION", "global")
DATA_STORE_ID = os.getenv("AGENT_BUILDER_DATA_STORE", "prison-policies-ds")
MODEL_LOCATION = os.getenv("GCP_MODEL_LOCATION", "global")

# Discovery Engine serving config
SERVING_CONFIG = (
    f"projects/{PROJECT_ID}/locations/{LOCATION}"
    f"/collections/default_collection/dataStores/{DATA_STORE_ID}"
    f"/servingConfigs/default_search"
)

CHAT_SYSTEM_PROMPT = (
    "You are a policy assistant. Answer questions using ONLY the policy "
    "documents provided. Cite document sections. If the answer is not in "
    "the documents, say so."
)


def _get_token() -> str:
    result = subprocess.run(
        [r"C:\CloudSDK\google-cloud-sdk\bin\gcloud.cmd", "auth", "print-access-token"],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gcloud auth failed: {result.stderr}")
    return result.stdout.strip()


def _search_data_store(query: str, page_size: int = 5) -> list[dict]:
    """Search the Agent Builder data store and return [{text, source}, ...]."""
    token = _get_token()
    url = (
        f"https://discoveryengine.googleapis.com/v1beta/"
        f"{SERVING_CONFIG}:search"
    )
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
        body = e.read().decode()[:1000]
        raise RuntimeError(f"Search API error {e.code}: {body}")

    contexts = []
    for r in result.get("results", []):
        doc = r.get("document", {}).get("derivedStructData", {})
        snippets = doc.get("snippets", [])
        text = " ".join(s.get("snippet", "") for s in snippets)
        if not text:
            text = json.dumps(doc.get("extractiveAnswers", [{}])[0].get("content", ""))
        title = doc.get("title", "") or (
            doc.get("structData", {}).get("title", "")
        )
        if text:
            contexts.append({"text": text, "source": title or "Policy Document"})
    return contexts


def retrieve_context(question: str, top_k: int = 5) -> list[dict]:
    """Retrieve relevant policy chunks as {text, source} dicts."""
    return _search_data_store(question, top_k)


def answer_question(question: str) -> dict:
    """Full pipeline: search Agent Builder → generate with Gemini.

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
