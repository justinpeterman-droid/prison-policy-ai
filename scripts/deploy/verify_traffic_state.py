"""Verify that Cloud Run traffic targets only reviewed revisions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-file", type=Path, required=True)
    parser.add_argument("--candidate-revision", required=True)
    parser.add_argument("--candidate-percent", type=int, required=True)
    parser.add_argument("--prior-revision")
    args = parser.parse_args()
    if not 0 <= args.candidate_percent <= 100:
        print("candidate percent is out of range", file=sys.stderr)
        return 1
    try:
        state = json.loads(args.state_file.read_text(encoding="utf-8"))
        traffic = state.get("status", {}).get("traffic", [])
        if not isinstance(traffic, list) or not traffic:
            raise ValueError("traffic state is missing")
        allocations: dict[str, int] = {}
        for target in traffic:
            revision = target.get("revision")
            percent = target.get("percent")
            if not isinstance(revision, str) or not isinstance(percent, int):
                raise ValueError("traffic target is malformed")
            allocations[revision] = allocations.get(revision, 0) + percent
        if sum(allocations.values()) != 100:
            raise ValueError("traffic does not total 100 percent")
        if allocations.get(args.candidate_revision, 0) != args.candidate_percent:
            raise ValueError("candidate allocation mismatch")
        allowed = {args.candidate_revision}
        if args.prior_revision:
            allowed.add(args.prior_revision)
            if allocations.get(args.prior_revision, 0) != 100 - args.candidate_percent:
                raise ValueError("prior allocation mismatch")
        if set(allocations) - allowed:
            raise ValueError("traffic includes an unreviewed revision")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"traffic verification failed: {exc}", file=sys.stderr)
        return 1
    print("traffic state verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
