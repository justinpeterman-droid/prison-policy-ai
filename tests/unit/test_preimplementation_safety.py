from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_unsafe_automatic_and_local_deployers_are_absent():
    for relative in (
        ".github/workflows/cloud-run.yml",
        "backend/scripts/deploy.sh",
        "scripts/merge_and_deploy.py",
    ):
        assert not (ROOT / relative).exists()


def test_pages_publishes_only_static_forms():
    workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    assert "frontend/forms" in workflow
    assert "path: ." not in workflow
    for forbidden in ("backend", "access-client", "infra", "release", "tests"):
        assert f"path: {forbidden}" not in workflow


def test_github_environment_policy_is_external_and_exact():
    policy = (ROOT / "docs" / "operations" / "github-environment-policy.md").read_text(
        encoding="utf-8"
    )
    assert (
        "GitHub administrators configure these environments outside Terraform and repository workflows."
        in policy
    )
    assert "Store completed records in the agency-approved system of record." in policy
    for environment in (
        "test",
        "production-plan",
        "production-apply",
        "production-deploy",
        "production-rollback",
        "access-release",
    ):
        assert f"| {environment} |" in policy
