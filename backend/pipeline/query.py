"""RAG query: retrieve + generate answers from policy corpus."""
import vertexai
from vertexai.preview import rag
from vertexai.generative_models import GenerativeModel
from backend.pipeline.config import (
    PROJECT_ID, LOCATION, GENERATION_MODEL, CORPUS_NAME
)

vertexai.init(project=PROJECT_ID, location=LOCATION)

CHAT_SYSTEM_PROMPT = (
    "You are a corrections policy assistant for the Arkansas Department of "
    "Correction. Answer questions using ONLY the policy documents provided. "
    "Cite document sections. If the answer is not in the documents, say so."
)


def _get_corpus():
    for c in rag.list_corpora():
        if c.display_name == CORPUS_NAME:
            return c
    raise RuntimeError(f"Corpus '{CORPUS_NAME}' not found. Run embed first.")


def retrieve_context(question: str, top_k: int = 5) -> list[str]:
    """Retrieve relevant policy chunks."""
    corpus = _get_corpus()
    response = rag.retrieval_query(
        rag_corpora=[corpus.name],
        text=question,
        similarity_top_k=top_k,
    )
    contexts = []
    if hasattr(response, 'contexts') and response.contexts:
        for ctx in response.contexts.contexts:
            contexts.append(ctx.text)
    return contexts


def answer_question(question: str) -> dict:
    """Full RAG pipeline: retrieve → generate, returns {answer, sources}."""
    contexts = retrieve_context(question)

    if not contexts:
        return {
            "answer": "No relevant policy documents found for this question.",
            "sources": []
        }

    context_text = "\n\n---\n\n".join(contexts)
    prompt = f"POLICY DOCUMENTS:\n{context_text}\n\nQUESTION: {question}"

    model = GenerativeModel(
        model_name=GENERATION_MODEL,
        system_instruction=CHAT_SYSTEM_PROMPT,
    )
    response = model.generate_content(prompt)

    return {
        "answer": response.text,
        "sources": [c[:80] + "..." for c in contexts]
    }
