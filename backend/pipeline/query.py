"""Agent Builder search — replaces raw RAG + Gemini with Vertex AI Agent Builder.

Uses Discovery Engine (discoveryengine.googleapis.com) for managed RAG.
Charges draw from the $1,000 Vertex AI Agent Builder credit.
"""
import os
import logging
import urllib.request
import urllib.error
import json

from backend.pipeline.config import PROJECT_ID

logger = logging.getLogger(__name__)

# Agent Builder data store ID — must match what was created in the console
DATA_STORE_ID = os.getenv("AGENT_BUILDER_DATA_STORE", "prison-policies-ds_1784585369312")
LOCATION = os.getenv("AGENT_BUILDER_LOCATION", "global")

# Serving config: Agent Builder auto-creates this when the data store is ready
SERVING_CONFIG = "default_search"

CHAT_SYSTEM_PROMPT = (
    "You are a policy assistant. Answer questions using ONLY the policy "
    "documents provided. Cite document sections. If the answer is not in "
    "the documents, say so. Be concise and use plain language."
)


def _get_access_token() -> str:
    """Get a fresh access token using the service account or ADC."""
    import subprocess
    result = subprocess.run(
        [r"/google-cloud-sdk/bin/gcloud", "auth", "print-access-token"],
        capture_output=True, text=True, timeout=15,
        env={
            **os.environ,
            "PATH": os.environ.get("PATH", "") + ":/google-cloud-sdk/bin",
        },
    )
    # Cloud Run provides ADC automatically, but we also try the gcloud fallback
    if result.returncode != 0:
        # Try ADC — works on Cloud Run automatically
        import google.auth
        import google.auth.transport.requests
        credentials, project = google.auth.default()
        credentials.refresh(google.auth.transport.requests.Request())
        return credentials.token
    return result.stdout.strip()


def search_documents(query: str, top_k: int = 5) -> list[dict]:
    """Search the Agent Builder data store for relevant policy documents.

    Returns list of {text, source} dicts.
    """
    token = _get_access_token()
    url = (
        f"https://discoveryengine.googleapis.com/v1beta/"
        f"projects/{PROJECT_ID}/locations/{LOCATION}/"
        f"dataStores/{DATA_STORE_ID}/"
        f"servingConfigs/{SERVING_CONFIG}:search"
    )

    body = {
        "query": query,
        "pageSize": top_k,
        "queryExpansionSpec": {"condition": "AUTO"},
        "spellCorrectionSpec": {"mode": "AUTO"},
        "contentSearchSpec": {
            "snippetSpec": {"returnSnippet": True},
            "summarySpec": {
                "summaryResultCount": 3,
                "includeCitations": True,
            },
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
    )
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    # Quota project header needed for on-prem ADC; harmless on Cloud Run
    req.add_header("X-Goog-User-Project", PROJECT_ID)

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        logger.error("Agent Builder search failed: %s %s", e.code, e.read().decode()[:500])
        return []
    except Exception as e:
        logger.error("Agent Builder search error: %s", e)
        return []

    contexts = []
    for r in result.get("results", []):
        doc = r.get("document", {})
        derived = doc.get("derivedStructData", {})

        # Extract the best text: summary > snippet > extracted text
        text = ""
        snippets = derived.get("snippets", [])
        if snippets:
            text = snippets[0].get("snippet", "")

        if not text:
            text = derived.get("extractiveAnswers", [{}])[0].get("content", "")

        if not text:
            # Fall back to document ID
            text = doc.get("id", "")[:200]

        source = doc.get("id", "Policy Document")
        # Clean up the source name
        if "/" in source:
            source = source.rsplit("/", 1)[-1]
        source = source.rsplit(".", 1)[0].replace("_", " ").strip()

        contexts.append({"text": text, "source": source})

    return contexts


def answer_question(question: str) -> dict:
    """Full pipeline: Agent Builder search → build answer with citations.

    Uses Agent Builder's built-in summarization for answer generation,
    with the system prompt injected as a preamble.

    Returns {answer, citations, sources}.
    """
    token = _get_access_token()
    url = (
        f"https://discoveryengine.googleapis.com/v1beta/"
        f"projects/{PROJECT_ID}/locations/{LOCATION}/"
        f"dataStores/{DATA_STORE_ID}/"
        f"servingConfigs/{SERVING_CONFIG}:search"
    )

    body = {
        "query": question,
        "pageSize": 5,
        "queryExpansionSpec": {"condition": "AUTO"},
        "spellCorrectionSpec": {"mode": "AUTO"},
        "contentSearchSpec": {
            "snippetSpec": {"returnSnippet": True, "maxSnippetCount": 2},
            "extractiveContentSpec": {"maxExtractiveAnswerCount": 1},
            "summarySpec": {
                "summaryResultCount": 3,
                "includeCitations": True,
                "modelSpec": {"version": "preview"},  # use latest summary model
            },
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
    )
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Goog-User-Project", PROJECT_ID)

    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        logger.error("Agent Builder search failed: %s", e.code)
        return {
            "answer": "Search is temporarily unavailable. Please try again.",
            "citations": [],
            "sources": [],
        }
    except Exception as e:
        logger.error("Agent Builder search error: %s", e)
        return {
            "answer": f"Search error: {e}",
            "citations": [],
            "sources": [],
        }

    # Build answer from summary + snippets
    summary = result.get("summary", {})
    summary_text = summary.get("summaryText", "")

    # Build citations from results
    citations = []
    sources = []
    for i, r in enumerate(result.get("results", []), 1):
        doc = r.get("document", {})
        derived = doc.get("derivedStructData", {})
        snippets = derived.get("snippets", [])

        text = snippets[0].get("snippet", "") if snippets else ""
        source = doc.get("id", f"Document {i}")
        if "/" in source:
            source = source.rsplit("/", 1)[-1]
        source = source.rsplit(".", 1)[0].replace("_", " ").strip()

        if text:
            citations.append({"n": i, "source": source, "text": text})
            sources.append(source)

    # Prepend system prompt context to the summary
    if summary_text:
        answer = (
            f"{CHAT_SYSTEM_PROMPT}\n\n"
            f"=== Search Results ===\n{summary_text}"
        )
        # Clean answer: strip the system prompt for display
        display_answer = summary_text
    else:
        # Fallback: build answer from snippets manually
        if not citations:
            return {
                "answer": "No relevant policy documents found for this question.",
                "citations": [],
                "sources": [],
            }
        parts = []
        for c in citations:
            parts.append(f"[{c['source']}] {c['text']}")
        display_answer = "Based on policy documents:\n\n" + "\n\n".join(parts)

    return {
        "answer": display_answer,
        "citations": citations,
        "sources": sources,
    }
