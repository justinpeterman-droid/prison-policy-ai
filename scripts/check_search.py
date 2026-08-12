"""Diagnose the policy-chat search path (RC-2).

Prints the resolved Agent Builder config, runs one trivial query against it, and
reports latency, raw hit count, and how many hits yielded usable passage text.
Use it when the chat says it found nothing, or returns a generic error: it tells
you *which* stage is broken — config, auth, retrieval, or text extraction.

It then runs the semantic reranker over those passages. That stage fails open
and silently, so a working chat is no evidence it is reaching the Ranking API —
this is the only way to see whether it is. A reranking failure does NOT affect
the exit code: the chat still works without it.

Needs GCP Application Default Credentials. Run from the repo root:

    PYTHONPATH=. python3 scripts/check_search.py
    PYTHONPATH=. python3 scripts/check_search.py "use of force"

Exit code is 0 when the search returns usable passages, 1 otherwise, so it can
double as a smoke check.
"""
import sys
import time

from backend.pipeline.config import search_config_summary
from backend.pipeline.query import _search_with_stats
from backend.pipeline.rerank import rerank_passages, rerank_status

DEFAULT_QUERY = "use of force"


def _report_rerank(query: str, passages: list[dict]) -> None:
    """Run the semantic reranker over the retrieved passages and show what it
    changed. Diagnostic only — reranking fails open, so a failure here means
    the chat is running on the retriever's ordering, not that it is broken."""
    print("\nSemantic reranking")
    print("-" * 60)
    status = rerank_status()
    if not status["enabled"]:
        print("  disabled via RERANK_ENABLED — retriever ordering is used as-is")
        return

    before = [p["source"] for p in passages]
    start = time.monotonic()
    reranked = rerank_passages(query, passages)
    elapsed = time.monotonic() - start
    status = rerank_status()  # re-read: a permanent failure disables it here

    reason = status["disabled_reason"]
    if reason:
        print(f"  UNAVAILABLE      {str(reason)[:200]}")
        print("  → The chat still works; passages just keep the retriever's order.")
        print(f"    Ranking config: {status['ranking_config']}")
        return

    after = [p["source"] for p in reranked]
    print(f"  latency          {elapsed:.2f}s")
    print(f"  model            {status['model']}")
    print(f"  order changed    {'yes' if after != before else 'no'}")
    if after != before:
        print("  new top sources:")
        for p in reranked[:5]:
            preview = " ".join(p["text"].split())[:80]
            print(f"    - {p['source']}: {preview}…")


def main(argv: list[str]) -> int:
    query = argv[1] if len(argv) > 1 else DEFAULT_QUERY

    print("Resolved search config")
    print("-" * 60)
    for key, value in search_config_summary().items():
        print(f"  {key:24} {value}")

    print(f"\nRunning query: {query!r}")
    print("-" * 60)
    start = time.monotonic()
    try:
        passages, raw_count = _search_with_stats(query, page_size=10)
    except Exception as e:  # noqa: BLE001 — diagnostic: report anything that fails
        elapsed = time.monotonic() - start
        print(f"  FAILED after {elapsed:.2f}s: {type(e).__name__}: {e}")
        print("\nThe log lines above name the serving config and the likely cause.")
        return 1
    elapsed = time.monotonic() - start

    print(f"  latency          {elapsed:.2f}s")
    print(f"  raw hits         {raw_count}")
    print(f"  usable passages  {len(passages)}")

    if raw_count and not passages:
        print("\n  → Search matched documents but no text could be read from them.")
        print("    The data store is likely not configured to return snippets or")
        print("    extractive content. Chat will look empty even though search works.")
        return 1
    if not raw_count:
        print("\n  → No documents matched. Either the corpus is empty/not indexed,")
        print("    or the engine id points somewhere unexpected.")
        return 1

    print("\n  Top sources:")
    for p in passages[:5]:
        preview = " ".join(p["text"].split())[:80]
        print(f"    - {p['source']}: {preview}…")
    print("\n  OK — search returned usable passages.")

    _report_rerank(query, passages)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
