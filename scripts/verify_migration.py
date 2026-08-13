"""Safe post-migration verification wrapper."""
from __future__ import annotations

import json

from backend.jobs.migration import verify


def main() -> int:
    try:
        result = verify()
    except Exception:
        print(json.dumps({"status": "database_unavailable"}))
        return 1
    print(json.dumps({"status": result["status"], "revision": result["revision"]}, sort_keys=True))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
