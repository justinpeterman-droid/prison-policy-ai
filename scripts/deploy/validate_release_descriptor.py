"""Validate the canonical version registry and immutable backend descriptor."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


VERSION_KEYS = {
    "$schema",
    "schema_version",
    "backend_version",
    "api_version",
    "client_version",
    "minimum_client_version",
    "minimum_server_version",
    "release_notes",
    "channel",
}
DESCRIPTOR_KEYS = {
    "schema_version",
    "source_commit",
    "image_digest",
    "sbom_sha256",
    "provenance_id",
    "migration_head",
    "api_version",
    "release_version",
    "version_registry_sha256",
    "test_workflow_run",
    "test_environment",
    "created_at",
    "creator_workflow",
}
SEMVER = re.compile(r"^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
IMAGE = re.compile(r"^[a-z0-9.-]+(?:/[a-z0-9._-]+)+@sha256:[0-9a-f]{64}$")
MIGRATION = re.compile(r"^[0-9]{8}_[0-9]{4}_[a-z0-9_]+$")
UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
DEVELOPMENT_VERSION = "0.0.0-development"


class ValidationError(ValueError):
    """Raised for a closed-contract validation failure."""


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"{path.name} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        missing = sorted(expected - set(value))
        extra = sorted(set(value) - expected)
        raise ValidationError(f"{label} keys do not match contract; missing={missing}, extra={extra}")


def validate_version_registry(path: Path, *, production: bool = False) -> tuple[dict[str, Any], str, dict[str, str]]:
    value = _read_json(path)
    _exact_keys(value, VERSION_KEYS, "version registry")
    if value["$schema"] != "./version.schema.json" or value["schema_version"] != 1:
        raise ValidationError("version registry schema identity is invalid")
    if value["api_version"] != "v1":
        raise ValidationError("api_version must be v1")
    for key in ("backend_version", "client_version", "minimum_client_version", "minimum_server_version"):
        if not isinstance(value[key], str) or not SEMVER.fullmatch(value[key]):
            raise ValidationError(f"{key} is not a supported semantic version")
    notes = value["release_notes"]
    if not isinstance(notes, str) or not 1 <= len(notes) <= 500 or any(ord(char) < 32 or ord(char) == 127 for char in notes):
        raise ValidationError("release_notes must be one safe line of 1-500 characters")
    if value["channel"] not in {"development", "pilot", "stable"}:
        raise ValidationError("channel is not approved")
    versions = [value[key] for key in ("backend_version", "client_version", "minimum_client_version", "minimum_server_version")]
    if production and (DEVELOPMENT_VERSION in versions or value["channel"] == "development"):
        raise ValidationError("production rejects development compatibility metadata")
    projection = {
        "RELEASE_VERSION": value["backend_version"],
        "API_VERSION": value["api_version"],
        "LATEST_CLIENT_VERSION": value["client_version"],
        "MINIMUM_CLIENT_VERSION": value["minimum_client_version"],
        "MINIMUM_SERVER_VERSION": value["minimum_server_version"],
        "RELEASE_NOTES": notes,
    }
    return value, _sha256(path), projection


def validate_descriptor(
    descriptor_path: Path,
    registry_path: Path,
    *,
    expected_descriptor_sha256: str | None = None,
    expected_image_digest: str | None = None,
    expected_migration_head: str | None = None,
    production: bool = False,
) -> dict[str, Any]:
    descriptor = _read_json(descriptor_path)
    _exact_keys(descriptor, DESCRIPTOR_KEYS, "backend descriptor")
    registry, registry_sha256, _ = validate_version_registry(registry_path, production=production)
    checks = {
        "schema_version": descriptor["schema_version"] == 1,
        "source_commit": isinstance(descriptor["source_commit"], str) and COMMIT.fullmatch(descriptor["source_commit"]),
        "image_digest": isinstance(descriptor["image_digest"], str) and IMAGE.fullmatch(descriptor["image_digest"]),
        "sbom_sha256": isinstance(descriptor["sbom_sha256"], str) and SHA256.fullmatch(descriptor["sbom_sha256"]),
        "provenance_id": isinstance(descriptor["provenance_id"], str) and 1 <= len(descriptor["provenance_id"]) <= 300,
        "migration_head": isinstance(descriptor["migration_head"], str) and MIGRATION.fullmatch(descriptor["migration_head"]),
        "api_version": descriptor["api_version"] == "v1",
        "release_version": isinstance(descriptor["release_version"], str) and SEMVER.fullmatch(descriptor["release_version"]),
        "version_registry_sha256": descriptor["version_registry_sha256"] == registry_sha256,
        "test_workflow_run": isinstance(descriptor["test_workflow_run"], str) and 1 <= len(descriptor["test_workflow_run"]) <= 300,
        "test_environment": descriptor["test_environment"] == "test",
        "created_at": isinstance(descriptor["created_at"], str) and UTC.fullmatch(descriptor["created_at"]),
        "creator_workflow": isinstance(descriptor["creator_workflow"], str) and 1 <= len(descriptor["creator_workflow"]) <= 300,
    }
    failed = sorted(key for key, result in checks.items() if not result)
    if failed:
        raise ValidationError(f"backend descriptor fields are invalid: {failed}")
    if descriptor["release_version"] != registry["backend_version"] or descriptor["api_version"] != registry["api_version"]:
        raise ValidationError("descriptor version projection does not match registry")
    if expected_descriptor_sha256 and _sha256(descriptor_path) != expected_descriptor_sha256:
        raise ValidationError("release descriptor SHA-256 mismatch")
    if expected_image_digest and descriptor["image_digest"] != expected_image_digest:
        raise ValidationError("release descriptor image digest mismatch")
    if expected_migration_head and descriptor["migration_head"] != expected_migration_head:
        raise ValidationError("release descriptor migration head mismatch")
    return descriptor


def _write_outputs(path: Path, values: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as output:
        for key, value in values.items():
            if "\n" in value or "\r" in value:
                raise ValidationError(f"output {key} is not a single safe line")
            output.write(f"{key}={value}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    version = subparsers.add_parser("version")
    version.add_argument("--registry", type=Path, required=True)
    version.add_argument("--expected-sha256")
    version.add_argument("--production", action="store_true")
    version.add_argument("--github-output", type=Path)
    descriptor = subparsers.add_parser("descriptor")
    descriptor.add_argument("--descriptor", type=Path, required=True)
    descriptor.add_argument("--registry", type=Path, required=True)
    descriptor.add_argument("--expected-descriptor-sha256")
    descriptor.add_argument("--expected-image-digest")
    descriptor.add_argument("--expected-migration-head")
    descriptor.add_argument("--production", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "version":
            _, registry_sha256, projection = validate_version_registry(args.registry, production=args.production)
            if args.expected_sha256 and args.expected_sha256 != registry_sha256:
                raise ValidationError("version registry SHA-256 mismatch")
            values = {"version_registry_sha256": registry_sha256, **projection}
            values["projection_json"] = json.dumps(projection, separators=(",", ":"), sort_keys=True)
            if args.github_output:
                _write_outputs(args.github_output, values)
            else:
                print(json.dumps(values, separators=(",", ":"), sort_keys=True))
        else:
            validate_descriptor(
                args.descriptor,
                args.registry,
                expected_descriptor_sha256=args.expected_descriptor_sha256,
                expected_image_digest=args.expected_image_digest,
                expected_migration_head=args.expected_migration_head,
                production=args.production,
            )
            print("backend release descriptor valid")
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"release validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
