import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "infra" / "terraform" / "modules" / "access_platform"


def read(name: str) -> str:
    return (MODULE / name).read_text(encoding="utf-8")


def test_cloud_run_ingress_and_digest_are_locked():
    serverless = read("serverless.tf")
    assert re.search(r'ingress\s*=\s*"INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"', serverless)
    assert re.search(r'ingress\s*=\s*"INGRESS_TRAFFIC_INTERNAL_ONLY"', serverless)
    assert len(re.findall(r"image\s*=\s*var\.image_digest", serverless)) == 2
    assert 'condition     = can(regex("@sha256:[0-9a-f]{64}$", var.image_digest))' in read("variables.tf")


def test_worker_has_no_public_invoker():
    terraform = "\n".join(path.read_text(encoding="utf-8") for path in MODULE.glob("*.tf"))
    bindings = re.findall(
        r'resource "google_cloud_run_v2_service_iam_member" "[^"]+" \{.*?\n\}',
        terraform,
        flags=re.DOTALL,
    )
    worker_bindings = [block for block in bindings if "google_cloud_run_v2_service.worker.name" in block]
    assert worker_bindings
    assert all("allUsers" not in block for block in worker_bindings)
    assert "task_invoker_service_account_email" in terraform


def test_storage_is_private_versioned_and_uniform():
    storage = read("storage.tf")
    assert 'resource "google_storage_bucket" "private"' in storage
    assert re.search(r"for_each\s*=\s*local\.storage_buckets", storage)
    assert len(re.findall(r'\b\w+\s*=\s*"access-\$\{var\.environment\}', storage)) == 5
    assert re.search(r'public_access_prevention\s*=\s*"enforced"', storage)
    assert re.search(r'uniform_bucket_level_access\s*=\s*true', storage)
    assert "versioning" in storage


def test_release_and_bootstrap_object_read_boundaries_are_narrow():
    storage = read("storage.tf")
    assert 'google_service_account.identities["api"].member' in storage
    assert 'role   = "roles/storage.objectViewer"' in storage
    assert 'google_service_account.identities["bootstrap"].member' in storage
    assert "admin-bootstrap-requests/" in storage
    assert "resource.name.startsWith" in storage
    for forbidden in ("roles/storage.objectAdmin", "roles/storage.admin", "allUsers"):
        assert forbidden not in storage


def test_compatibility_environment_projection_is_complete():
    serverless = read("serverless.tf")
    for name, variable in {
        "RELEASE_VERSION": "release_version",
        "API_VERSION": "api_version",
        "LATEST_CLIENT_VERSION": "latest_client_version",
        "MINIMUM_CLIENT_VERSION": "minimum_client_version",
        "MINIMUM_SERVER_VERSION": "minimum_server_version",
        "RELEASE_NOTES": "release_notes",
    }.items():
        assert re.search(rf'name\s*=\s*"{name}"', serverless)
        assert re.search(rf"value\s*=\s*var\.{variable}", serverless)
