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
import re
from urllib.parse import urlparse

# Known officer slang → formal policy terms to add to the search query.
# Keys are lowercase phrases matched on WORD BOUNDARIES; values are appended.
# Curated toward the high-value, safety-critical mappings (PREA / use of force
# / contraband / escape).
#
# Every trigger must be unambiguous in ordinary speech. Bare "jumped", "took
# off" and "shouldn't have" used to live here and fired on sentences with
# nothing to do with policy — "the inmate jumped down from the top bunk" was
# searched as an assault, "he took off his jacket" as an escape. Injecting the
# wrong policy vocabulary is worse than injecting none: it pulls the retriever
# toward documents that don't answer the question.
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
    "jumped him": "use of force assault",
    "jumped on": "use of force assault",
    "shank": "contraband weapon confiscation",
    "walked off": "escape walkaway",
    "took off running": "escape walkaway",
    "cheeked": "contraband medication diversion",
    "keistered": "contraband concealment search",
    "hooch": "contraband intoxicant manufacture",
    "cuff up": "restraint application inmate compliance",
    "gassed": "use of force chemical agent",
    "shakedown": "search contraband cell shakedown",
}

# Built once. \b on both ends so "date an inmate" still matches inside a
# sentence, but "gate" never matches inside "gateway".
_SLANG_PATTERNS = [(re.compile(rf"\b{re.escape(trigger)}\b"), formal) for trigger, formal in SLANG_GLOSSARY.items()]


def augment_query(question: str) -> str:
    """Append formal policy terms for any known slang found in the question.

    Additive and deduped; returns the question unchanged when nothing matches.
    Matching is on word boundaries — a substring match fires on unrelated
    sentences and steers retrieval toward the wrong policy.
    """
    q = question or ""
    q_lower = q.lower()
    extra: list[str] = [formal for pattern, formal in _SLANG_PATTERNS if pattern.search(q_lower)]
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


def _truncate(text: str, max_chars: int) -> str:
    """Trim to `max_chars`, preferring the last sentence boundary.

    Cutting mid-sentence invites the model to complete a policy statement it
    can't actually see, so prefer to end where the source did.
    """
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    window = text[:max_chars]
    cut = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
    # Only honour a sentence break if it isn't discarding most of the passage.
    if cut > max_chars // 2:
        return window[: cut + 1]
    return window.rstrip() + "…"


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


def _segment_texts(derived: dict) -> list[str]:
    return _contents_of(
        _get_any(derived, "extractive_segments", "extractiveSegments"),
        "content",
        "text",
    )


def _answer_texts(derived: dict) -> list[str]:
    # ALL extractive answers, not just the first — each is a separate passage.
    return _contents_of(_get_any(derived, "extractive_answers", "extractiveAnswers"), "content", "text")


# Preference order for passage text, richest first.
#
#   segments — verbatim chunks of the document: the actual policy language.
#   answers  — focused spans the retriever judged responsive.
#   snippets — short keyword-in-context fragments, heavily elided with "…".
#
# Snippets used to win, which meant the generator usually reasoned over clipped
# fragments even when the full passage was right there in the same response.
# That produces hedged, thin answers and gives the citation pane little to show.
_PASSAGE_SOURCES = (_segment_texts, _answer_texts, _snippet_texts)


def extract_passage_text(document: dict, max_chars: int = 0) -> str:
    """Best-effort passage text for one search-result document.

    Prefers the richest available form (segments → extractive answers →
    snippets), then falls back to raw document content. Returns '' only when the
    document genuinely carries no usable text.

    `max_chars` (when > 0) truncates on a sentence boundary where possible, so a
    single very long segment can't crowd the prompt.
    """
    if not isinstance(document, dict):
        return ""
    derived = document.get("derivedStructData") or {}
    struct = document.get("structData") or {}

    for source in _PASSAGE_SOURCES:
        parts = source(derived)
        if parts:
            return _truncate(" ".join(parts), max_chars)

    # Raw indexed content, then any plain text carried on the structs.
    content = document.get("content") or {}
    raw = _get_any(content, "raw_text", "rawText") if isinstance(content, dict) else None
    if isinstance(raw, str) and raw.strip():
        return _truncate(raw.strip(), max_chars)

    for data in (derived, struct):
        v = _get_any(data, "content", "text", "raw_text", "rawText", "body")
        if isinstance(v, str) and v.strip():
            return _truncate(v.strip(), max_chars)

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
    link = _get_any(derived, "link", "uri", "url") or _get_any(struct, "link", "uri", "url")
    if isinstance(link, str) and link.strip():
        path = urlparse(link).path or link
        name = posixpath.basename(path.rstrip("/"))
        if name:
            return name
    return DEFAULT_SOURCE_LABEL


def parse_search_results(payload: dict, max_chars: int = 0) -> list[dict]:
    """Turn a Discovery Engine search payload into [{text, source}, ...].

    Only documents with no usable text anywhere are dropped. `max_chars` caps
    each individual passage (0 = no cap).
    """
    contexts: list[dict] = []
    for r in (payload or {}).get("results", []) or []:
        document = (r or {}).get("document") or {}
        text = extract_passage_text(document, max_chars=max_chars)
        if not text:
            continue
        contexts.append({"text": text, "source": extract_source_label(document)})
    return contexts


# ── Conversation history ────────────────────────────────────────────────────

# Officers ask short follow-ups ("what about a female inmate?", "and if he
# refuses?") that are meaningless standalone. Only a few turns are needed to
# resolve them, and history is strictly context for reading the question — it is
# never a source of policy (see the prompt in query.py).
MAX_HISTORY_TURNS = 4
MAX_HISTORY_CHARS = 1500
MAX_HISTORY_ANSWER_CHARS = 400


def format_history(
    history: list[dict] | None,
    max_turns: int = MAX_HISTORY_TURNS,
    max_chars: int = MAX_HISTORY_CHARS,
) -> str:
    """Render recent turns as a compact transcript for the generation prompt.

    Accepts [{"question": ..., "answer": ...}] (what the chat client keeps).
    Keeps the most recent turns, oldest-first in the output, dropping the oldest
    first when the character budget is hit — the nearest turn is the one a
    pronoun usually refers to.
    """
    if not history:
        return ""
    turns: list[tuple[str, str]] = []
    for item in list(history)[-max_turns:]:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "").strip()
        answer = str(item.get("answer") or "").strip()
        if question:
            turns.append((question, answer))
    if not turns:
        return ""

    blocks: list[str] = []
    total = 0
    for question, answer in reversed(turns):  # budget from the newest backwards
        answer = _truncate(answer, MAX_HISTORY_ANSWER_CHARS)
        block = f"Officer: {question}\nAssistant: {answer}" if answer else f"Officer: {question}"
        if blocks and total + len(block) > max_chars:
            break
        blocks.append(block)
        total += len(block)
    return "\n\n".join(reversed(blocks))


def select_passages(contexts: list[dict], k: int, max_per_source: int = 3, max_total_chars: int = 0) -> list[dict]:
    """Pick the top `k` passages to feed the generator.

    Drops empty and exact-duplicate (source, text) passages, and caps passages
    per source at `max_per_source` so one document can't dominate. Keeps the
    retriever's ordering (assumed already relevance-ranked).

    `max_total_chars` (when > 0) also bounds the combined size of the selected
    passages. Now that passages are full segments rather than clipped snippets,
    passage *count* alone no longer bounds the prompt — the first passage always
    survives, so a single oversized one still gets through rather than leaving
    the generator with nothing.

    Hitting the character budget STOPS selection rather than skipping past the
    oversized passage to smaller ones further down. Skipping quietly inverted
    relevance: a long, highly-ranked passage — which in policy is usually the
    actual rule with its conditions and exceptions — was dropped so that two
    lower-ranked one-liners could fit. Truncation to `MAX_PASSAGE_CHARS` already
    happens upstream, so a passage that still doesn't fit is genuinely large.
    """
    seen: set[tuple[str, str]] = set()
    per_source: dict[str, int] = {}
    out: list[dict] = []
    total = 0
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
        if max_total_chars > 0 and out and total + len(text) > max_total_chars:
            break
        seen.add(key)
        per_source[src] = per_source.get(src, 0) + 1
        total += len(text)
        out.append(c)
        if len(out) >= k:
            break
    return out
