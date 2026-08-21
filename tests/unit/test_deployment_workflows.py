import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
RUNTIME_DIGEST = "53757bfb153c99eb7005963b7e4ea3a8ba488badceab8487d3ba982ad54f2047"
CONTROLLED_WORKFLOWS = (
    "terraform-plan.yml",
    "terraform-apply.yml",
    "deploy-test.yml",
    "rollback-test.yml",
    "deploy-production.yml",
    "rollback-production.yml",
    "bootstrap-first-admin.yml",
)


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
    assert "EXPECTED_TEST_COMMIT" in text
    assert ".test_workflow_run" in text
    assert ".creator_workflow" in text


def test_test_deploy_validates_the_same_patched_runtime_as_the_production_image():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    deploy_test = workflow("deploy-test.yml")
    digest = f"sha256:{RUNTIME_DIGEST}"
    assert f"FROM chainguard/python@{digest}" in dockerfile
    assert deploy_test.count(digest) == 3
    assert "8fab86fb761aeb18723f4f1b1baa330bd59d64e92abdc5b980d1bbd9399c297d" not in deploy_test


def test_production_uses_staged_traffic_and_rolls_back_on_failed_smoke():
    text = workflow("deploy-production.yml")
    for allocation in ["1", "10", "50", "100"]:
        assert f"candidate={allocation}" in text
    assert "rollback-production.yml" in text or "prior_api_revision" in text
    assert text.count("--max-error-rate") == 4
    assert text.count("--max-p95-latency-ms") == 4
    assert "PRODUCTION_CANARY_OBSERVATION_SECONDS" in text


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


def test_test_plan_receives_all_real_environment_inputs_without_fixture_defaults():
    test_root = (ROOT / "infra" / "terraform" / "environments" / "test" / "main.tf").read_text(encoding="utf-8")
    test_plan = workflow("terraform-plan.yml").split("  plan_production:", 1)[0]
    for variable in (
        "storage_log_bucket_name",
        "artifact_registry_kms_key_name",
        "managed_hostname",
        "dns_zone_name",
        "image_repository_id",
        "agent_builder_engine_id",
        "billing_account_id",
        "bootstrap_request_uri",
    ):
        assert f"= var.{variable}" in test_root
        assert f"TF_VAR_{variable}" in test_plan
    assert "fixture-engine" not in test_root
    assert "fixture-billing-account" not in test_root


def test_no_workflow_uses_long_lived_keys_or_destructive_commands():
    combined = "\n".join(workflow(name) for name in CONTROLLED_WORKFLOWS)
    for forbidden in ["GCP_SA_KEY", "service_account_key", "terraform destroy", "alembic downgrade", "git push", "git merge"]:
        assert forbidden not in combined


def test_controlled_workflows_have_no_ordinary_push_trigger_and_pin_every_action():
    for name in CONTROLLED_WORKFLOWS:
        text = workflow(name)
        assert "\n  push:" not in text
        for action in re.findall(r"^\s*uses:\s*([^\s#]+)", text, re.MULTILINE):
            assert re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", action)


def test_plan_and_apply_permissions_and_artifact_authority_are_closed():
    plan = workflow("terraform-plan.yml")
    apply = workflow("terraform-apply.yml")
    for permission in ("contents: read", "actions: read", "id-token: write", "deployments: write"):
        assert permission in plan
    for permission in ("contents: read", "actions: read", "deployments: read", "id-token: write"):
        assert permission in apply
    assert "workflow_dispatch:" not in apply
    assert "actions/artifacts/${PLAN_ARTIFACT_ID}" in apply
    assert "workflow_run.id" in apply
    assert "expired" in apply
    assert "is_symlink" in apply
    assert "terraform -chdir=\"${{ inputs.terraform_root }}\" apply" in apply
    assert "terraform plan" not in apply
    assert "raw-plan.json" in plan
    assert "resource_change_count" in plan
    assert "rm raw-plan.txt raw-plan.json" in plan


def test_registry_and_descriptor_schemas_are_closed_and_exact():
    registry_schema = json.loads((ROOT / "release" / "version.schema.json").read_text(encoding="utf-8"))
    descriptor_schema = json.loads((ROOT / "release" / "backend-release.schema.json").read_text(encoding="utf-8"))
    registry = json.loads((ROOT / "release" / "version.json").read_text(encoding="utf-8"))
    assert registry_schema["additionalProperties"] is False
    assert descriptor_schema["additionalProperties"] is False
    assert set(registry_schema["required"]) == set(registry)
    assert registry["backend_version"] == "0.0.0-development"
    assert registry["channel"] == "development"
    assert set(descriptor_schema["required"]) == set(descriptor_schema["properties"])


def test_production_validation_rejects_checked_in_development_registry():
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "deploy" / "validate_release_descriptor.py"),
            "version",
            "--registry",
            str(ROOT / "release" / "version.json"),
            "--production",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "production rejects development" in result.stderr


def test_bootstrap_has_exact_inputs_and_static_environment_jobs():
    text = workflow("bootstrap-first-admin.yml")
    dispatch = text.split("jobs:", 1)[0]
    assert set(re.findall(r"^      ([a-z0-9_]+):\s*$", dispatch, re.MULTILINE)) == {
        "target_environment",
        "request_uri",
        "expected_sha256",
    }
    assert text.count("gcloud run jobs execute access-test-bootstrap-admin") == 1
    assert text.count("gcloud run jobs execute access-production-bootstrap-admin") == 1
    assert "gcloud run jobs describe" not in text
    assert "gcloud logging" not in text


def test_rollback_workflows_do_not_build_apply_or_invoke_jobs():
    combined = workflow("rollback-test.yml") + workflow("rollback-production.yml")
    for forbidden in ("docker build", "terraform apply", "run jobs execute", "secrets versions", "--source"):
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
