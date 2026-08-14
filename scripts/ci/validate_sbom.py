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
REDACTED_STRUCTURE = {"env", "environment", "content", "contents", "filecontent", "filecontents"}


def contains_redacted_structure(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            key.lower().replace("_", "") in REDACTED_STRUCTURE or contains_redacted_structure(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(contains_redacted_structure(child) for child in value)
    return False


def has_image_identity(data: dict[str, object], image_id: str, image: str) -> bool:
    return any(
        isinstance(item, dict) and item.get("comment") == f"op07-image-config={image_id}; image-reference={image}"
        for item in data.get("annotations", [])
    )


def validate(args: argparse.Namespace) -> int:
    if not Path(args.output).is_file():
        print("SBOM output is absent", file=sys.stderr)
        return 1
    output = Path(args.output)
    try:
        data = json.loads(output.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        print("SBOM output is not valid UTF-8 SPDX JSON", file=sys.stderr)
        return 1
    if (
        not isinstance(data, dict)
        or not data.get("spdxVersion", "").startswith("SPDX-")
        or not data.get("name")
        or not data.get("documentNamespace")
        or not data.get("packages")
        or contains_redacted_structure(data)
    ):
        print("SBOM metadata or redaction contract failed", file=sys.stderr)
        return 1
    rendered = json.dumps(data)

    def inspect(image: str) -> dict[str, object]:
        return json.loads(subprocess.check_output(["docker", "image", "inspect", image], text=True))[0]

    image = inspect(args.image)
    runtime = inspect(args.runtime_image)
    image_id = str(image["Id"])
    runtime_id = str(runtime["Id"])
    runtime_digests = runtime.get("RepoDigests") or []
    image_layers = image["RootFS"]["Layers"]
    runtime_layers = runtime["RootFS"]["Layers"]
    provenance_path = Path(args.provenance)
    if args.generate_provenance:
        if (
            not any(digest.endswith("@" + DIGEST) for digest in runtime_digests)
            or image_layers[: len(runtime_layers)] != runtime_layers
        ):
            print("runtime image does not resolve to approved digest", file=sys.stderr)
            return 1
        data.setdefault("annotations", []).append(
            {
                "annotator": "Tool: op07-sbom-validator",
                "annotationDate": "2026-08-13T00:00:00Z",
                "annotationType": "OTHER",
                "comment": f"op07-image-config={image_id}; image-reference={args.image}",
            }
        )
        output.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
        provenance_path.write_text(
            json.dumps(
                {
                    "image": args.image,
                    "image_id": image_id,
                    "sbom_image_identity": f"op07-image-config={image_id}; image-reference={args.image}",
                    "runtime_image": args.runtime_image,
                    "runtime_id": runtime_id,
                    "runtime_repo_digests": runtime_digests,
                    "image_layers": image_layers,
                    "runtime_layers": runtime_layers,
                    "runtime_digest": DIGEST,
                    "sbom_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                    "tool": "syft-spdx",
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return 0
    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        print("SBOM provenance binding failed", file=sys.stderr)
        return 1
    if (
        not has_image_identity(data, image_id, args.image)
        or provenance.get("image_id") != image_id
        or provenance.get("sbom_image_identity") != f"op07-image-config={image_id}; image-reference={args.image}"
        or provenance.get("runtime_id") != runtime_id
        or provenance.get("runtime_repo_digests") != runtime_digests
        or not any(digest.endswith("@" + DIGEST) for digest in runtime_digests)
        or provenance.get("image_layers") != image_layers
        or provenance.get("runtime_layers") != runtime_layers
        or image_layers[: len(runtime_layers)] != runtime_layers
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--provenance", required=True)
    parser.add_argument("--runtime-image", required=True)
    parser.add_argument("--generate-provenance", action="store_true")
    return validate(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
