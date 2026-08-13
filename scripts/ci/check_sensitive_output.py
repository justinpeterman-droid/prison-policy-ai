"""Fail closed when publishable output contains secret-like or personal fields."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = (
    "password", "private_key", "authorization", "bearer", "service_account",
    "access_code", "admin_code", "temporary_pin", "employee_id", "inmate_id",
)
BINARY_SUFFIXES = {".accdb", ".png", ".jpg", ".jpeg", ".webp", ".docx", ".pdf", ".mp4", ".woff", ".woff2"}
STRUCTURED_SUFFIXES = {".json", ".sarif", ".spdx"}
FIXTURE_VALUE = re.compile(r"(?:fixture-|fake-|fictional-)[a-z0-9_-]+|local-(?:user|admin)|slut", re.I)
ASSIGNMENT = re.compile(
    rf"\b(?:{'|'.join(map(re.escape, FORBIDDEN))})\b\s*[:=]\s*(?:"
    r"(os\.getenv\(\s*(?:'[^']*'|\"[^\"]*\")(?:\s*,\s*(?:'[^']*'|\"[^\"]*\"))?\s*\))"
    r"|['\"]([^'\"]+)['\"]|([^\s,;}\]]+))", re.I,
)
GETENV_VALUE = re.compile(
    r"^os\.getenv\(\s*(?:'[^']*'|\"[^\"]*\")(?:\s*,\s*(?:'(?P<single>[^']*)'|\"(?P<double>[^\"]*)\"))?\s*\)$", re.I,
)


def is_explicitly_nonsecret(value: str) -> bool:
    normalized = value.strip().strip("`;,")
    if normalized.lower().startswith("os.getenv("):
        getenv = GETENV_VALUE.fullmatch(normalized)
        if not getenv:
            return False
        fallback = next((part for part in getenv.groupdict().values() if part is not None), None)
        return fallback is None or not fallback.strip() or bool(FIXTURE_VALUE.fullmatch(fallback.strip()))
    return bool(
        not normalized
        or normalized in {'""', "''", "str", "Bearer", "UpdateGrant", "!0"}
        or FIXTURE_VALUE.fullmatch(normalized)
        or normalized.startswith(("request.", "google_", "generate_temporary_pin(", "${", "<"))
    )


def paths(args: argparse.Namespace) -> list[Path]:
    if args.tracked:
        result = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True)
        return [ROOT / entry for entry in result.stdout.splitlines()]
    return [Path(value) for value in args.paths]


def structured_values(value: object) -> list[str]:
    """Return every non-fixture value under a forbidden JSON/SPDX/SARIF key."""
    bad: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN:
                if isinstance(child, (dict, list)):
                    bad.append(key)
                elif not is_explicitly_nonsecret(str(child)):
                    bad.append(key)
            bad.extend(structured_values(child))
    elif isinstance(value, list):
        for child in value:
            bad.extend(structured_values(child))
    return bad


def scan(path: Path, *, strict_structured: bool) -> bool:
    if not path.exists() or not path.is_file():
        return False
    if path.suffix.lower() in BINARY_SUFFIXES:
        return True
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    if strict_structured and path.suffix.lower() in STRUCTURED_SUFFIXES:
        try:
            if structured_values(json.loads(text)):
                return False
        except json.JSONDecodeError:
            return False
    for line in text.splitlines():
        values = (next(part for part in match.groups() if part is not None) for match in ASSIGNMENT.finditer(line))
        if any(
            not is_explicitly_nonsecret(value)
            and (strict_structured or not value.strip().startswith(("{", "[")))
            for value in values
        ):
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tracked", action="store_true")
    parser.add_argument("--paths", nargs="+")
    args = parser.parse_args()
    if not args.tracked and not args.paths:
        parser.error("one scan target is required")
    bad: list[str] = []
    for candidate in paths(args):
        members = candidate.rglob("*") if candidate.is_dir() else [candidate]
        for path in members:
            if path.is_dir():
                continue
            relative = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
            if args.tracked and ("tests" in relative.parts or path.suffix.lower() in STRUCTURED_SUFFIXES):
                continue
            if not scan(path, strict_structured=not args.tracked):
                bad.append(str(path))
    if bad:
        print("sensitive-output gate failed:\n" + "\n".join(bad), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
