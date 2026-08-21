"""Create a closed backend release descriptor from tested immutable evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from validate_release_descriptor import validate_descriptor, validate_version_registry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version-registry", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--sbom-sha256", required=True)
    parser.add_argument("--provenance-id", required=True)
    parser.add_argument("--migration-head", required=True)
    parser.add_argument("--test-workflow-run", required=True)
    parser.add_argument("--creator-workflow", required=True)
    parser.add_argument("--created-at")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    registry, registry_sha256, _ = validate_version_registry(args.version_registry)
    created_at = args.created_at or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    descriptor = {
        "schema_version": 1,
        "source_commit": args.source_commit,
        "image_digest": args.image_digest,
        "sbom_sha256": args.sbom_sha256,
        "provenance_id": args.provenance_id,
        "migration_head": args.migration_head,
        "api_version": registry["api_version"],
        "release_version": registry["backend_version"],
        "version_registry_sha256": registry_sha256,
        "test_workflow_run": args.test_workflow_run,
        "test_environment": "test",
        "created_at": created_at,
        "creator_workflow": args.creator_workflow,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(descriptor, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    validate_descriptor(args.output, args.version_registry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
