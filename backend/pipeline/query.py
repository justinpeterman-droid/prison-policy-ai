"""RAG query: retrieve + generate answers from policy corpus."""
import vertexai
from vertexai.preview import rag
from vertexai.generative_models import GenerativeModel
from backend.pipeline.config import (
    PROJECT_ID, LOCATION, GENERATION_MODEL, CORPUS_NAME
)

vertexai.init(project=PROJECT_ID, location=LOCATION)

CHAT_SYSTEM_PROMPT = (
    "You are a policy assistant. Answer questions using ONLY the policy "
    "documents provided. Cite document sections. If the answer is not in "
    "the documents, say so."
)


def _get_corpus():
    for c in rag.list_corpora():
        if c.display_name == CORPUS_NAME:
            return c
    raise RuntimeError(f"Corpus '{CORPUS_NAME}' not found. Run embed first.")


def _source_label(ctx) -> str:
    """Best-effort human-readable source name for a retrieved chunk.

    Vertex RAG contexts may expose a display name or a gs:// URI depending on
    how the corpus was imported; fall back to empty string when neither is
    present (the UI then labels it generically).
    """
    for attr in ("source_display_name", "source_uri"):
        val = getattr(ctx, attr, "") or ""
        if val:
            # Strip any path/bucket prefix and extension for a clean label.
            name = val.rstrip("/").split("/")[-1]
            return name.rsplit(".", 1)[0].replace("_", " ").strip()
    return ""


def retrieve_context(question: str, top_k: int = 5) -> list[dict]:
    """Retrieve relevant policy chunks as {text, source} dicts."""
    corpus = _get_corpus()
    response = rag.retrieval_query(
        rag_corpora=[corpus.name],
        text=question,
        similarity_top_k=top_k,
    )
    contexts = []
    if hasattr(response, 'contexts') and response.contexts:
        for ctx in response.contexts.contexts:
            contexts.append({"text": ctx.text, "source": _source_label(ctx)})
    return contexts


def answer_question(question: str) -> dict:
    """Full RAG pipeline: retrieve → generate.

    Returns {answer, citations, sources}:
      - citations: [{n, source, text}] full retrieved passages, for the UI's
        cited-policy pane (click a citation → view/highlight the exact passage)
      - sources: short labels, kept for backward compatibility
    """
    contexts = retrieve_context(question)

    if not contexts:
        return {
            "answer": "No relevant policy documents found for this question.",
            "citations": [],
            "sources": [],
        }

    context_text = "\n\n---\n\n".join(c["text"] for c in contexts)
    prompt = f"POLICY DOCUMENTS:\n{context_text}\n\nQUESTION: {question}"

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
