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
FIXTURE_VALUE = re.compile(r"^\s*(?:fixture-|fake-|fictional-)[a-z0-9_-]+|local-(?:user|admin)|fx[a-z0-9]{4}|slut\s*$", re.I)
ASSIGNMENT = re.compile(
    r"\b(?:password|private_key|authorization|bearer|service_account|access_code|admin_code|temporary_pin|employee_id|inmate_id)\b\s*[:=]\s*(?:"
    r"(os\.getenv\(\s*(?:'[^']*'|\"[^\"]*\")(?:\s*,\s*(?:'[^']*'|\"[^\"]*\"))?\s*\))"
    r"|['\"]([^'\"]+)['\"]|([^\s,;}\]]+))",
    re.I,
)
GETENV_VALUE = re.compile(
    r"^os\.getenv\(\s*(?:'[^']*'|\"[^\"]*\")(?:\s*,\s*(?:'(?P<single>[^']*)'|\"(?P<double>[^\"]*)\"))?\s*\)$",
    re.I,
)


def is_explicitly_nonsecret(value: str) -> bool:
    """Permit only source syntax that cannot itself contain a credential value."""
    normalized = value.strip().strip("`;,")
    if normalized.lower().startswith("os.getenv("):
        getenv = GETENV_VALUE.fullmatch(normalized)
        if not getenv:
            return False
        fallback = next((part for part in getenv.groupdict().values() if part is not None), None)
        return fallback is None or not fallback.strip() or bool(FIXTURE_VALUE.fullmatch(fallback.strip()))
    if (
        not normalized
        or normalized in {'""', "''", "str", "string", "boolean", "number", "Bearer", "UpdateGrant", "!0"}
        or re.fullmatch(r"[0-9]", normalized)
        or FIXTURE_VALUE.fullmatch(normalized)
    ):
        return True
    return normalized.startswith(("request.", "google_", "generate_temporary_pin(", "z.", "${", "{", "[", "<"))


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
                strict = path.suffix.lower() in {".sarif", ".log"} or "output" in path.parts
                assignment_values = (
                    next(part for part in match.groups() if part is not None) for match in ASSIGNMENT.finditer(line)
                )
                if any(not is_explicitly_nonsecret(value) for value in assignment_values):
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
