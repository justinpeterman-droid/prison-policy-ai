"""Preimplementation deployment safety contracts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_automatic_cloud_run_deployer_is_absent():
    assert not (ROOT / ".github" / "workflows" / "cloud-run.yml").exists()
