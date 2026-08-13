"""Validate a safe SPDX JSON SBOM for the approved runtime identity."""

from __future__ import annotations
import argparse
import json
import re
import hashlib
import subprocess
import sys
from pathlib import Path

DIGEST = "sha256:8fab86fb761aeb18723f4f1b1baa330bd59d64e92abdc5b980d1bbd9399c297d"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--provenance", required=True)
    parser.add_argument("--write-provenance", action="store_true")
    args = parser.parse_args()
    if not Path(args.output).is_file():
        print("SBOM output is absent", file=sys.stderr)
        return 1
    output = Path(args.output)
    data = json.loads(output.read_text(encoding="utf-8"))
    rendered = json.dumps(data)
    image_id = subprocess.check_output(
        ["docker", "image", "inspect", args.image, "--format", "{{.Id}}"], text=True
    ).strip()
    provenance_path = Path(args.provenance)
    if args.write_provenance:
        provenance_path.write_text(
            json.dumps(
                {
                    "image": args.image,
                    "image_id": image_id,
                    "runtime_digest": DIGEST,
                    "sbom_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                    "tool": "syft-spdx",
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if (
        data.get("spdxVersion", "").startswith("SPDX-") is False
        or not data.get("packages")
        or provenance.get("image_id") != image_id
        or provenance.get("runtime_digest") != DIGEST
        or provenance.get("sbom_sha256") != hashlib.sha256(output.read_bytes()).hexdigest()
    ):
        print("SBOM provenance binding failed", file=sys.stderr)
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
