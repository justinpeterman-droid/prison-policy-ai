"""Preimplementation deployment safety contracts."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_automatic_cloud_run_deployer_is_absent():
    assert not (ROOT / ".github" / "workflows" / "cloud-run.yml").exists()


def test_terraform_ignores_only_revision_image_and_traffic():
    serverless = (ROOT / "infra" / "terraform" / "modules" / "access_platform" / "serverless.tf").read_text(encoding="utf-8")
    lifecycle_blocks = []
    cursor = 0
    while True:
        start = serverless.find("lifecycle {", cursor)
        if start < 0:
            break
        depth = 0
        end = start
        for end in range(start, len(serverless)):
            if serverless[end] == "{":
                depth += 1
            elif serverless[end] == "}":
                depth -= 1
                if depth == 0:
                    break
        lifecycle_blocks.append(serverless[start : end + 1])
        cursor = end + 1
    assert len(lifecycle_blocks) == 2
    for block in lifecycle_blocks:
        assert "template[0].containers[0].image" in block
        assert "traffic" in block
        for forbidden in ("iam", "ingress", "secret", "service_account", "scaling", "env"):
            assert forbidden not in block


def test_deploy_act_as_is_scoped_to_api_and_worker_runtime_identities():
    serverless = (ROOT / "infra" / "terraform" / "modules" / "access_platform" / "serverless.tf").read_text(encoding="utf-8")
    assert 'resource "google_service_account_iam_member" "deploy_runtime_user"' in serverless
    assert "api    = google_service_account.api.name" in serverless
    assert "worker = google_service_account.worker.name" in serverless
    assert 'role               = "roles/iam.serviceAccountUser"' in serverless
    assert 'member             = google_service_account.workflow["deploy"].member' in serverless
