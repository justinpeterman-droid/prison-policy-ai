import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "infra" / "terraform" / "modules" / "access_platform"


def read(name: str) -> str:
    return (MODULE / name).read_text(encoding="utf-8")


def test_sql_is_postgres_17_private_and_protected():
    sql = read("sql.tf")
    assert re.search(r'database_version\s*=\s*"POSTGRES_17"', sql)
    assert re.search(r"ipv4_enabled\s*=\s*false", sql)
    assert re.search(r'availability_type\s*=\s*var\.environment == "production" \? "REGIONAL" : "ZONAL"', sql)
    assert re.search(r'deletion_protection\s*=\s*var\.environment == "production"', sql)
    assert re.search(r"point_in_time_recovery_enabled\s*=\s*true", sql)
    assert re.search(r"disk_autoresize\s*=\s*true", sql)


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
        assert f'google_service_account.identities["{identity}"].member' not in secret_bindings
    assert re.search(r'role\s*=\s*"roles/viewer"', identities)
    assert re.search(r'role\s*=\s*google_project_iam_custom_role\.rollback_traffic\.name', identities)


def test_workflow_impersonation_is_scoped_to_the_exact_workflow_ref():
    identities = read("identities.tf")
    assert 'attribute.job_workflow_ref/${one(var.wif_trust[each.key].workflow_refs)}' in identities


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
    assert re.search(r'role\s*=\s*"roles/secretmanager\.secretVersionAdder"', initial_pin)
    assert 'google_service_account.identities["bootstrap"].member' in initial_pin
    assert "secretAccessor" not in initial_pin
    assert re.search(r'role\s*=\s*"roles/secretmanager\.secretAccessor"', update_key)
    assert 'google_service_account.identities["api"].member' in update_key
    assert 'google_service_account.identities["bootstrap"].member' not in update_key
    assert 'google_service_account.identities["admin_bootstrap"].member' not in update_key
