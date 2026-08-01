"""Pure retrieval helpers for the policy chat — no AI, no GCP.

Three jobs, all deterministic and unit-tested:

  * augment_query — map known officer slang to formal policy terms and APPEND
    them to the question (never replace it). Discovery Engine already understands
    the natural question; this just nudges the right policy vocabulary in, with
    no extra LLM round-trip (the old _expand_query made a Gemini call and threw
    the question away).

  * parse_search_results — turn a raw Discovery Engine search payload into
    [{text, source}]. Deliberately forgiving: the API exposes passage text under
    several different shapes (snippets / extractive answers / extractive
    segments / raw content) and spells the keys inconsistently, so a hit whose
    text lives in an unexpected place must still be usable rather than silently
    dropped — dropping it makes retrieval look empty when it actually worked.

  * select_passages — trim the retrieved results fed to the generator: drop
    exact duplicates and cap how many come from any one source, so a single
    document can't crowd out other relevant policies. Preserves the retriever's
    (semantic) ordering.
"""
from __future__ import annotations

import posixpath
from urllib.parse import urlparse

# Known officer slang → formal policy terms to add to the search query.
# Keys are lowercase substrings; values are appended (additive, so a stray
# match only broadens search slightly). Curated toward the high-value,
# safety-critical mappings (PREA / use of force / contraband / escape).
SLANG_GLOSSARY: dict[str, str] = {
    "hooking up": "PREA sexual misconduct staff inmate",
    "hook up": "PREA sexual misconduct staff inmate",
    "sleeping with": "PREA sexual misconduct staff inmate",
    "messing around": "PREA sexual misconduct",
    "romantic": "PREA sexual misconduct",
    "dating": "PREA sexual misconduct undue familiarity",
    "date an inmate": "PREA sexual misconduct undue familiarity",
    "relationship with an inmate": "PREA sexual misconduct undue familiarity",
    "give an inmate a ride": "undue familiarity fraternization",
    "bring them food": "undue familiarity fraternization",
    "beat down": "use of force inmate altercation",
    "beatdown": "use of force inmate altercation",
    "jumped": "use of force assault",
    "shank": "contraband weapon confiscation",
    "shouldn't have": "contraband",
    "walked off": "escape walkaway",
    "took off": "escape walkaway",
}


def augment_query(question: str) -> str:
    """Append formal policy terms for any known slang found in the question.

    Additive and deduped; returns the question unchanged when nothing matches.
    """
    q = (question or "")
    q_lower = q.lower()
    extra: list[str] = []
    for trigger, formal in SLANG_GLOSSARY.items():
        if trigger in q_lower:
            extra.append(formal)
    if not extra:
        return q
    # Dedupe individual terms while preserving order.
    seen: dict[str, None] = {}
    for term in " ".join(extra).split():
        seen.setdefault(term, None)
    return (q + " " + " ".join(seen)).strip()


# ── Search-response parsing ─────────────────────────────────────────────────
#
# Discovery Engine returns passage text under several shapes, and the keys
# inside the derived Struct come back camelCase or snake_case depending on the
# field and API version. Every lookup below therefore tries both spellings.

DEFAULT_SOURCE_LABEL = "Policy Document"


def _get_any(data: dict, *names: str):
    """First present, non-empty value among `names`."""
    if not isinstance(data, dict):
        return None
    for n in names:
        v = data.get(n)
        if v:
            return v
    return None


def _contents_of(items, *keys: str) -> list[str]:
    """Pull text out of a list of {content: ...}-style entries (or bare strings)."""
    out: list[str] = []
    for item in items or []:
        if isinstance(item, str):
            if item.strip():
                out.append(item.strip())
            continue
        if not isinstance(item, dict):
            continue
        for k in keys:
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                out.append(v.strip())
                break
    return out


def _snippet_texts(derived: dict) -> list[str]:
    """Snippet strings, skipping the NO_SNIPPET_AVAILABLE placeholders the API
    returns when it has a hit but could not build a snippet for it."""
    out: list[str] = []
    for s in _get_any(derived, "snippets") or []:
        if not isinstance(s, dict):
            if isinstance(s, str) and s.strip():
                out.append(s.strip())
            continue
        status = str(s.get("snippet_status") or s.get("snippetStatus") or "").upper()
        if status and status not in ("SUCCESS", "SNIPPET_STATUS_UNSPECIFIED"):
            continue
        snip = s.get("snippet")
        if isinstance(snip, str) and snip.strip():
            out.append(snip.strip())
    return out


def extract_passage_text(document: dict) -> str:
    """Best-effort passage text for one search-result document.

    Tries, in order: snippets → extractive answers → extractive segments → raw
    document content/struct text. Returns '' only when the document genuinely
    carries no usable text.
    """
    if not isinstance(document, dict):
        return ""
    derived = document.get("derivedStructData") or {}
    struct = document.get("structData") or {}

    parts = _snippet_texts(derived)
    if parts:
        return " ".join(parts)

    # ALL extractive answers, not just the first — each is a separate passage.
    parts = _contents_of(
        _get_any(derived, "extractive_answers", "extractiveAnswers"),
        "content", "text")
    if parts:
        return " ".join(parts)

    parts = _contents_of(
        _get_any(derived, "extractive_segments", "extractiveSegments"),
        "content", "text")
    if parts:
        return " ".join(parts)

    # Raw indexed content, then any plain text carried on the structs.
    content = document.get("content") or {}
    raw = _get_any(content, "raw_text", "rawText") if isinstance(content, dict) else None
    if isinstance(raw, str) and raw.strip():
        return raw.strip()

    for source in (derived, struct):
        v = _get_any(source, "content", "text", "raw_text", "rawText", "body")
        if isinstance(v, str) and v.strip():
            return v.strip()

    return ""


def extract_source_label(document: dict) -> str:
    """Human-readable source label for a search-result document."""
    if not isinstance(document, dict):
        return DEFAULT_SOURCE_LABEL
    derived = document.get("derivedStructData") or {}
    struct = document.get("structData") or {}

    title = _get_any(derived, "title") or _get_any(struct, "title")
    if isinstance(title, str) and title.strip():
        return title.strip()

    # Fall back to the file name from the document's link/uri.
    link = (_get_any(derived, "link", "uri", "url")
            or _get_any(struct, "link", "uri", "url"))
    if isinstance(link, str) and link.strip():
        path = urlparse(link).path or link
        name = posixpath.basename(path.rstrip("/"))
        if name:
            return name
    return DEFAULT_SOURCE_LABEL


def parse_search_results(payload: dict) -> list[dict]:
    """Turn a Discovery Engine search payload into [{text, source}, ...].

    Only documents with no usable text anywhere are dropped.
    """
    contexts: list[dict] = []
    for r in (payload or {}).get("results", []) or []:
        document = (r or {}).get("document") or {}
        text = extract_passage_text(document)
        if not text:
            continue
        contexts.append({"text": text, "source": extract_source_label(document)})
    return contexts


def select_passages(contexts: list[dict], k: int, max_per_source: int = 3) -> list[dict]:
    """Pick the top `k` passages to feed the generator.

    Drops empty and exact-duplicate (source, text) passages, and caps passages
    per source at `max_per_source` so one document can't dominate. Keeps the
    retriever's ordering (assumed already relevance-ranked).
    """
    seen: set[tuple[str, str]] = set()
    per_source: dict[str, int] = {}
    out: list[dict] = []
    for c in contexts:
        text = (c.get("text") or "").strip()
        src = c.get("source") or ""
        if not text:
            continue
        key = (src, text)
        if key in seen:
            continue
        if per_source.get(src, 0) >= max_per_source:
            continue
        seen.add(key)
        per_source[src] = per_source.get(src, 0) + 1
        out.append(c)
        if len(out) >= k:
            break
    return out
