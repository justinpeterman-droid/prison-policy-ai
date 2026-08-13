"""Dispatch available report-job outbox rows to private Cloud Tasks."""

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.jobs.dispatcher import dispatch_pending  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)
    summary = dispatch_pending(limit=args.limit)
    print(f"dispatched={summary.dispatched} failed={summary.failed} pending={summary.pending}")
    return 0 if summary.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
