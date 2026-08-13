"""Fail closed when publishable output contains secret-like or personal fields."""

from __future__ import annotations
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = (
    "password",
    "private_key",
    "authorization",
    "bearer",
    "service_account",
    "access_code",
    "admin_code",
    "temporary_pin",
    "employee_id",
    "inmate_id",
)
FIXTURE_VALUE = re.compile(r"^\s*(?:fixture-|fake-)[a-z0-9_-]+\s*$", re.I)
ASSIGNMENT = re.compile(
    r"\b(?:password|private_key|authorization|bearer|service_account|access_code|admin_code|temporary_pin)\b\s*[:=]\s*['\"]([^'\"]+)['\"]",
    re.I,
)


def paths(args: argparse.Namespace) -> list[Path]:
    if args.tracked:
        result = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True)
        return [ROOT / entry for entry in result.stdout.splitlines()]
    return [Path(value) for value in args.paths]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tracked", action="store_true")
    parser.add_argument("--paths", nargs="+")
    args = parser.parse_args()
    if not args.tracked and not args.paths:
        parser.error("one scan target is required")
    bad = []
    for candidate in paths(args):
        candidates = candidate.rglob("*") if candidate.is_dir() else [candidate]
        for path in candidates:
            if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".webp", ".docx", ".pdf"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for line in text.splitlines():
                lowered = line.lower()
                value = ASSIGNMENT.search(line)
                strict = path.suffix.lower() in {".sarif", ".json", ".log"} or "output" in path.parts
                if value and not FIXTURE_VALUE.fullmatch(value.group(1)):
                    bad.append(str(path))
                    break
                if strict and any(re.search(rf"\b{re.escape(term)}\b\s*[:=]", lowered) for term in FORBIDDEN):
                    bad.append(str(path))
                    break
    if bad:
        print("sensitive-output gate failed:\n" + "\n".join(bad), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
