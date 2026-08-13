"""Validate a safe SPDX JSON SBOM for the approved runtime identity."""

from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

DIGEST = "sha256:8fab86fb761aeb18723f4f1b1baa330bd59d64e92abdc5b980d1bbd9399c297d"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not Path(args.output).is_file():
        print("SBOM output is absent", file=sys.stderr)
        return 1
    data = json.loads(Path(args.output).read_text(encoding="utf-8"))
    rendered = json.dumps(data)
    dockerfile = (Path(__file__).resolve().parents[2] / "Dockerfile").read_text(encoding="utf-8")
    if (
        data.get("spdxVersion", "").startswith("SPDX-") is False
        or not data.get("packages")
        or f"chainguard/python@{DIGEST}" not in dockerfile
    ):
        print("SBOM must contain SPDX metadata and packages for the approved runtime digest", file=sys.stderr)
        return 1
    if any("licenseDeclared" not in package or "licenseConcluded" not in package for package in data["packages"]):
        print("SBOM package license metadata missing", file=sys.stderr)
        return 1
    if re.search(r"(password|private_key|authorization|bearer)", rendered, re.I):
        print("SBOM contains sensitive data", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
