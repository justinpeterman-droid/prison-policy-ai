"""Reject mutable GitHub Action references."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN = re.compile(r"^\s*uses:\s*[^@\s]+@[0-9a-f]{40}(?:\s+#.*)?$", re.MULTILINE)


def main() -> int:
    bad = []
    for workflow in (ROOT / ".github" / "workflows").glob("*.yml"):
        for line in workflow.read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("uses:") and not PIN.match(line):
                bad.append(f"{workflow.relative_to(ROOT)}: {line.strip()}")
    if bad:
        print("Mutable or malformed action pins:\n" + "\n".join(bad), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
