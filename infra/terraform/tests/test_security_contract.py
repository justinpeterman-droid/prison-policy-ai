import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "infra" / "terraform" / "modules" / "access_platform"


def read(name: str) -> str:
    return (MODULE / name).read_text(encoding="utf-8")


def test_sql_is_postgres_17_private_and_protected():
    sql = read("sql.tf")
    assert 'database_version = "POSTGRES_17"' in sql
    assert "ipv4_enabled    = false" in sql
    assert 'availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"' in sql
    assert 'deletion_protection = var.environment == "production"' in sql
    assert "point_in_time_recovery_enabled = true" in sql
    assert "disk_autoresize = true" in sql


def test_terraform_never_manages_secret_values_or_keys():
    terraform = "\n".join(path.read_text(encoding="utf-8") for path in MODULE.glob("*.tf"))
    assert "google_secret_manager_secret_version" not in terraform
    assert "google_service_account_key" not in terraform
    assert "github_repository_environment" not in terraform
    assert "roles/owner" not in terraform.lower()
    assert "roles/editor" not in terraform.lower()


def test_runtime_identities_are_single_purpose():
    identities = read("identities.tf")
    assert 'environment_id = var.environment == "production" ? "prod" : "test"' in identities
    for role_id in ["api", "worker", "task-invoker", "migration", "bootstrap", "tf-plan", "tf-apply", "deploy", "rollback", "admin-bootstrap", "release"]:
        assert f'"{role_id}"' in identities
    assert 'account_id   = "access-${local.environment_id}-${each.value}"' in identities
    assert 'workload_identity_pool_id = "access-${local.environment_id}-wif"' in identities


def test_workflow_identities_have_distinct_wif_and_secret_boundaries():
    identities = read("identities.tf")
    outputs = read("outputs.tf")
    for identity in ("terraform_plan", "terraform_apply", "deploy", "rollback", "admin_bootstrap", "access_release"):
        assert f'output "{identity}_service_account_email"' in outputs
        assert f'output "{identity}_wif_provider_name"' in outputs
    secret_bindings = "\n".join(re.findall(
        r'resource "google_secret_manager_secret_iam_member" "[^"]+" \{.*?\n\}',
        identities,
        flags=re.DOTALL,
    ))
    for identity in ("terraform_plan", "terraform_apply", "deploy", "rollback", "admin_bootstrap", "access_release"):
        assert f"google_service_account.{identity}.member" not in secret_bindings
    assert 'role = "roles/viewer"' in identities
    assert 'role = google_project_iam_custom_role.rollback_traffic.name' in identities


def test_bootstrap_and_update_grant_secrets_are_separated():
    identities = read("identities.tf")
    secrets = read("secrets.tf")
    assert 'secret_id = "initial-admin-pin"' in secrets
    assert 'secret_id = "client-update-grant-key"' in secrets
    bindings = re.findall(
        r'resource "google_secret_manager_secret_iam_member" "[^"]+" \{.*?\n\}',
        identities,
        flags=re.DOTALL,
    )
    initial_pin = next(block for block in bindings if "initial_admin_pin.id" in block)
    update_key = next(block for block in bindings if "client_update_grant_key.id" in block)
    assert 'role = "roles/secretmanager.secretVersionAdder"' in initial_pin
    assert "google_service_account.bootstrap.member" in initial_pin
    assert "secretAccessor" not in initial_pin
    assert 'role = "roles/secretmanager.secretAccessor"' in update_key
    assert "google_service_account.api.member" in update_key
    assert "google_service_account.bootstrap.member" not in update_key
    assert "google_service_account.admin_bootstrap.member" not in update_key
