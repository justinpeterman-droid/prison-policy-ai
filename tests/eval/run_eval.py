#!/usr/bin/env python3
"""Policy-chat eval harness.

Runs curated questions (cases.jsonl) through the live chat pipeline and scores
three things: gate accuracy, retrieval hit-rate, and answer correctness. Writes
a per-case JSON report and prints a scorecard.

REQUIRES GCP ADC (Discovery Engine + Gemini) — the same credentials the chat
feature itself needs. Without them the calls 500 and every content case errors.
The scoring logic (scorer.py) is pure and is unit-tested separately in CI.

Usage:
    PYTHONPATH=. python3 tests/eval/run_eval.py
    PYTHONPATH=. python3 tests/eval/run_eval.py --cases tests/eval/cases.jsonl
    PYTHONPATH=. python3 tests/eval/run_eval.py --gate-only     # gate routing only
    PYTHONPATH=. python3 tests/eval/run_eval.py --id prea_dating  # a single case
    PYTHONPATH=. python3 tests/eval/run_eval.py --no-rerank     # reranker off

To measure what semantic reranking is worth, run the set twice — once plain,
once with --no-rerank — and compare retrieval hit-rate and answer pass-rate.
Reranking only reorders retrieved passages, so it cannot change which documents
were found; what it changes is which of them reach the generator.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tests.eval.scorer import (  # noqa: E402
    score_answer, score_retrieval, score_gate, summarize,
)

CASES_PATH = Path(__file__).parent / "cases.jsonl"
OUTPUT_DIR = Path(__file__).parent / "output"


def load_cases(path: Path) -> list[dict]:
    cases = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            cases.append(json.loads(line))
    return cases


def run(cases: list[dict], gate_only: bool = False) -> list[dict]:
    # Imported here (not at module top) so the file is importable without the
    # Vertex SDK; these calls are what actually need GCP ADC.
    from backend.pipeline.query import answer_question, _classify_query

    results = []
    for c in cases:
        r = {"id": c.get("id"), "question": c.get("question")}

        # ── Gate ──
        if "gate" in c:
            expected_work = c["gate"] == "work"
            try:
                actual_work = _classify_query(c["question"])
                r["gate_ok"] = score_gate(expected_work, actual_work)
                r["gate_actual"] = "work" if actual_work else "off_topic"
            except Exception as e:  # ADC missing / classifier error
                r["gate_error"] = str(e)

        # Off-topic cases and --gate-only stop here (no answer expected).
        if gate_only or c.get("gate") == "off_topic":
            results.append(r)
            continue

        # ── Search + generate ──
        try:
            res = answer_question(c["question"])
        except Exception as e:
            r["error"] = str(e)
            results.append(r)
            continue

        answer = res.get("answer", "")
        # Measure retrieval on everything that was retrieved, not just what the
        # answer cited — so a retrieval miss is distinguishable from a citation miss.
        retrieved = res.get("retrieved_sources") or res.get("sources", [])
        r["n_retrieved"] = len(retrieved)
        r["n_citations"] = len(res.get("citations", []))
        r["answer_preview"] = answer[:240]

        if "expect_sources" in c:
            rr = score_retrieval(c["expect_sources"], retrieved)
            r["retrieval_hit"] = rr["hit"]
            r["retrieval_matched"] = rr["matched"]

        sa = score_answer(answer, c.get("must_contain"), c.get("must_not_contain"))
        r["answer_pass"] = sa["passed"]
        r["answer_missing"] = sa["missing"]
        r["answer_forbidden"] = sa["forbidden_present"]

        results.append(r)
    return results


def _print_scorecard(results: list[dict], scorecard: dict) -> None:
    def pct(v):
        return "n/a" if v is None else f"{v * 100:.0f}%"

    print("\n" + "=" * 60)
    print("  POLICY-CHAT EVAL SCORECARD")
    print("=" * 60)
    print(f"  cases:              {scorecard['n']}")
    print(f"  reranking:          {'on' if scorecard.get('rerank') else 'OFF'}")
    print(f"  gate accuracy:      {pct(scorecard['gate_accuracy'])}")
    print(f"  retrieval hit-rate: {pct(scorecard['retrieval_hit_rate'])}")
    print(f"  answer pass-rate:   {pct(scorecard['answer_pass_rate'])}")
    print("-" * 60)
    for r in results:
        flags = []
        if r.get("gate_ok") is False:
            flags.append(f"GATE→{r.get('gate_actual')}")
        if r.get("retrieval_hit") is False:
            flags.append("NO-RETRIEVAL")
        if r.get("answer_pass") is False:
            if r.get("answer_missing"):
                flags.append(f"MISSING:{r['answer_missing']}")
            if r.get("answer_forbidden"):
                flags.append(f"FORBIDDEN:{r['answer_forbidden']}")
        if r.get("error"):
            flags.append(f"ERROR:{r['error'][:40]}")
        status = "ok  " if not flags else "FAIL"
        print(f"  [{status}] {r['id']}  {' '.join(flags)}")
    print("=" * 60)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the policy-chat eval set")
    ap.add_argument("--cases", default=str(CASES_PATH))
    ap.add_argument("--gate-only", action="store_true",
                    help="Only score gate routing (fewer LLM calls)")
    ap.add_argument("--id", help="Run a single case by id")
    ap.add_argument("--no-rerank", action="store_true",
                    help="Disable semantic reranking, for an A/B against the "
                         "default run")
    args = ap.parse_args()

    # Set before anything imports backend.pipeline.config, which reads this at
    # import time — run() does the backend imports lazily for exactly this kind
    # of reason.
    if args.no_rerank:
        os.environ["RERANK_ENABLED"] = "0"

    cases = load_cases(Path(args.cases))
    if args.id:
        cases = [c for c in cases if c.get("id") == args.id]
        if not cases:
            print(f"No case with id={args.id!r}")
            return 1

    t0 = time.time()
    results = run(cases, gate_only=args.gate_only)
    scorecard = summarize(results)
    scorecard["elapsed_s"] = round(time.time() - t0, 1)
    # Stamped into results.json so an A/B pair of runs is self-describing — two
    # scorecards with no record of which one had reranking on are not a
    # comparison.
    scorecard["rerank"] = not args.no_rerank

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / "results.json"
    out.write_text(json.dumps(
        {"scorecard": scorecard, "results": results}, indent=2), encoding="utf-8")

    _print_scorecard(results, scorecard)
    print(f"  wrote {out}  ({scorecard['elapsed_s']}s)")

    # Non-zero exit if any hard failure, so CI/scripts can gate on it.
    hard_fail = any(
        r.get("gate_ok") is False or r.get("answer_pass") is False
        for r in results
    )
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
