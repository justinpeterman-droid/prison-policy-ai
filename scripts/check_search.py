"""Diagnose the policy-chat search path (RC-2).

Prints the resolved Agent Builder config, runs one trivial query against it, and
reports latency, raw hit count, and how many hits yielded usable passage text.
Use it when the chat says it found nothing, or returns a generic error: it tells
you *which* stage is broken — config, auth, retrieval, or text extraction.

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

DEFAULT_QUERY = "use of force"


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
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
