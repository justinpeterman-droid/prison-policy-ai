"""Deployment metadata contracts for traceable review records."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_cloud_run_deploy_stamps_the_source_commit():
    workflow = (ROOT / ".github" / "workflows" / "cloud-run.yml").read_text(
        encoding="utf-8")

    assert "--update-env-vars SOURCE_COMMIT=${{ github.sha }}" in workflow
