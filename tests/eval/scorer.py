"""Deterministic scoring for the policy-chat eval harness.

No AI, no GCP — pure functions, so they unit-test in CI and give a stable,
repeatable signal. The runner (run_eval.py) drives the live pipeline and feeds
its output here.

Three signals:
  * gate accuracy    — did the gate route work vs off-topic correctly?
  * retrieval hit    — did search surface at least one expected source?
  * answer pass      — does the answer state required facts and avoid forbidden ones?
"""
from __future__ import annotations


def _norm(s) -> str:
    return (s or "").lower()


def contains_any(text: str, alternatives) -> bool:
    """True if `text` contains any of `alternatives` (case-insensitive).

    `alternatives` may be a single string or a list of synonyms — the check
    passes if ANY synonym is present. This lets a requirement be satisfied by
    e.g. either "PREA" or "Prison Rape Elimination Act".
    """
    t = _norm(text)
    if isinstance(alternatives, str):
        alternatives = [alternatives]
    return any(_norm(a) in t for a in alternatives)


def score_answer(answer: str, must_contain=None, must_not_contain=None) -> dict:
    """Check required facts are present and forbidden phrasings are absent.

    must_contain:     list of requirements; each is a string OR a list of
                      synonyms (requirement passes if any synonym appears).
    must_not_contain: list of phrases that must NOT appear. Substring match,
                      not semantics — use specific affirmative phrasings
                      (e.g. "is allowed", not bare "allowed", which also
                      matches "not allowed").
    """
    must_contain = must_contain or []
    must_not_contain = must_not_contain or []
    missing = [req for req in must_contain if not contains_any(answer, req)]
    forbidden = [p for p in must_not_contain if contains_any(answer, p)]
    return {
        "passed": not missing and not forbidden,
        "missing": missing,
        "forbidden_present": forbidden,
    }


def score_retrieval(expect_sources, retrieved_sources) -> dict:
    """Did retrieval surface at least one expected source?

    expect_sources:    keywords we expect in a relevant doc's title/source label.
    retrieved_sources: the source labels actually returned by search.
    A 'hit' = any expected keyword appears in any retrieved source. Returns
    hit=None when the case declares no expectation (so it's excluded from rates).
    """
    expect_sources = expect_sources or []
    joined = " || ".join(_norm(s) for s in (retrieved_sources or []))
    matched = [kw for kw in expect_sources if _norm(kw) in joined]
    return {
        "hit": (bool(matched) if expect_sources else None),
        "matched": matched,
        "expected": expect_sources,
    }


def score_gate(expected_work: bool, actual_work: bool) -> bool:
    """True when the gate's work/off-topic decision matches expectation."""
    return bool(expected_work) == bool(actual_work)


def summarize(results: list[dict]) -> dict:
    """Aggregate per-case results into a scorecard (rates ignore N/A cases)."""
    def rate(key):
        vals = [r[key] for r in results if r.get(key) is not None]
        return round(sum(1 for v in vals if v) / len(vals), 3) if vals else None
    return {
        "n": len(results),
        "gate_accuracy": rate("gate_ok"),
        "retrieval_hit_rate": rate("retrieval_hit"),
        "answer_pass_rate": rate("answer_pass"),
    }
