"""Safe post-migration verification wrapper."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    from backend.jobs.migration import verify

    try:
        result = verify()
    except Exception:
        print(json.dumps({"status": "database_unavailable"}))
        return 1
    print(json.dumps({"status": result["status"], "revision": result["revision"]}, sort_keys=True))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
