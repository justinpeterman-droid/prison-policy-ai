"""Reject mutable workflow action and external image references."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTION = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)(?:\s+#.*)?$")
IMAGE = re.compile(r"^\s*image:\s*[\"']?([^\s\"'#]+)")
PULL = re.compile(r"\bdocker\s+pull\s+([^\s\\]+)")
SHA = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
DIGEST = re.compile(r"^[^@\s]+@sha256:[0-9a-f]{64}$")


def check(root: Path) -> list[str]:
    bad: list[str] = []
    workflow_dir = root / ".github" / "workflows"
    for workflow in sorted((*workflow_dir.rglob("*.yml"), *workflow_dir.rglob("*.yaml"))):
        relative = workflow.relative_to(root)
        for number, line in enumerate(workflow.read_text(encoding="utf-8").splitlines(), start=1):
            action = ACTION.match(line)
            if action and not SHA.fullmatch(action.group(1)):
                bad.append(f"{relative}:{number}: mutable action {action.group(1)}")
            image = IMAGE.match(line)
            if image and not DIGEST.fullmatch(image.group(1)):
                bad.append(f"{relative}:{number}: mutable image {image.group(1)}")
            for pulled in PULL.findall(line):
                if not DIGEST.fullmatch(pulled):
                    bad.append(f"{relative}:{number}: mutable image {pulled}")
    return bad


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    bad = check(args.root.resolve())
    if bad:
        print("Mutable or malformed workflow pins:\n" + "\n".join(bad), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
