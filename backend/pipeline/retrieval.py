"""Pure retrieval helpers for the policy chat — no AI, no GCP.

Two jobs, both deterministic and unit-tested:

  * augment_query — map known officer slang to formal policy terms and APPEND
    them to the question (never replace it). Discovery Engine already understands
    the natural question; this just nudges the right policy vocabulary in, with
    no extra LLM round-trip (the old _expand_query made a Gemini call and threw
    the question away).

  * select_passages — trim the retrieved results fed to the generator: drop
    exact duplicates and cap how many come from any one source, so a single
    document can't crowd out other relevant policies. Preserves the retriever's
    (semantic) ordering.
"""
from __future__ import annotations

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
