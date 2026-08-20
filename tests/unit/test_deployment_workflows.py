from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_production_is_manual_protected_and_digest_only():
    text = workflow("deploy-production.yml")
    assert "workflow_dispatch:" in text
    assert "environment: production-deploy" in text
    assert "@sha256:" in text
    assert "--source" not in text
    assert "--no-traffic" in text
    assert "SOURCE_COMMIT" in text
    assert "RELEASE_VERSION" in text
    assert "MINIMUM_SERVER_VERSION" in text
    assert "RELEASE_NOTES" in text


def test_production_uses_staged_traffic_and_rolls_back_on_failed_smoke():
    text = workflow("deploy-production.yml")
    for allocation in ["1", "10", "50", "100"]:
        assert f"candidate={allocation}" in text
    assert "rollback-production.yml" in text or "prior_api_revision" in text


def test_old_bypass_deployers_are_removed():
    assert not (WORKFLOWS / "cloud-run.yml").exists()
    assert not (ROOT / "backend" / "scripts" / "deploy.sh").exists()
    assert not (ROOT / "scripts" / "merge_and_deploy.py").exists()


def test_plan_apply_handoff_is_bound_to_origin_run_and_exact_artifact():
    plan = workflow("terraform-plan.yml")
    apply = workflow("terraform-apply.yml")
    production = workflow("deploy-production.yml")
    for field in (
        "plan_workflow_run_id",
        "plan_workflow_name",
        "plan_workflow_id",
        "plan_artifact_id",
        "plan_artifact_name",
        "plan_sha256",
    ):
        assert field in plan
        assert field in apply
        assert field in production
    for check in (
        "github.repository",
        "workflow_id",
        "conclusion",
        "protected_environment",
        "git_ref",
        "source_commit",
        "plan_sha256",
    ):
        assert check in apply
    assert "artifact-id" in plan
    assert "artifact-ids:" in apply
    assert "plan_artifact_name" in apply
    assert "download by name" not in apply.lower()


def test_version_registry_is_the_only_projection_source():
    combined = "\n".join(workflow(name) for name in (
        "terraform-plan.yml",
        "deploy-test.yml",
        "rollback-test.yml",
        "deploy-production.yml",
    ))
    assert "release/version.json" in combined
    assert "version_registry_sha256" in combined
    for name in (
        "RELEASE_VERSION",
        "LATEST_CLIENT_VERSION",
        "MINIMUM_CLIENT_VERSION",
        "MINIMUM_SERVER_VERSION",
        "API_VERSION",
        "RELEASE_NOTES",
    ):
        assert name in combined
    assert "inputs.release_version" not in combined


def test_no_workflow_uses_long_lived_keys_or_destructive_commands():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in WORKFLOWS.glob("*.yml"))
    for forbidden in ["GCP_SA_KEY", "service_account_key", "terraform destroy", "alembic downgrade", "git push", "git merge"]:
        assert forbidden not in combined


def test_first_admin_bootstrap_is_manual_protected_and_pin_blind():
    text = workflow("bootstrap-first-admin.yml")
    assert "workflow_dispatch:" in text
    assert "target_environment:" in text
    assert "request_uri:" in text
    assert "expected_sha256:" in text
    assert "environment: test" in text
    assert "environment: production-deploy" in text
    assert "access-test-bootstrap-admin" in text
    assert "access-production-bootstrap-admin" in text
    assert "GCP_ADMIN_BOOTSTRAP_WIF_PROVIDER" in text
    assert "GCP_ADMIN_BOOTSTRAP_SERVICE_ACCOUNT" in text
    assert "--wait" in text
    for forbidden in (
        "push:",
        "staff_member_id",
        "approval_reference",
        "temporary_pin",
        "gcloud secrets versions access",
        "continue-on-error",
    ):
        assert forbidden not in text
