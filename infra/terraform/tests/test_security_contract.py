import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "infra" / "terraform" / "modules" / "access_platform"
PRODUCTION_ROOT = ROOT / "infra" / "terraform" / "environments" / "production"
TEST_ROOT = ROOT / "infra" / "terraform" / "environments" / "test"


def read(name: str) -> str:
    return (MODULE / name).read_text(encoding="utf-8")


def variable_block(source: str, name: str) -> str:
    match = re.search(rf'variable\s+"{re.escape(name)}"\s*\{{', source)
    assert match, f"missing variable {name}"

    depth = 0
    for index in range(match.end() - 1, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start(): index + 1]
    raise AssertionError(f"unterminated variable {name}")


def test_production_requires_external_log_and_kms_inputs():
    production = (PRODUCTION_ROOT / "variables.tf").read_text(encoding="utf-8")

    for name in ("storage_log_bucket_name", "artifact_registry_kms_key_name"):
        block = variable_block(production, name)
        assert "default" not in block
        assert re.search(r"nullable\s*=\s*false", block)


def test_managed_buckets_forward_access_logs_to_external_destination():
    storage = read("storage.tf")
    bootstrap = (ROOT / "infra" / "terraform" / "bootstrap" / "state" / "main.tf").read_text(encoding="utf-8")

    assert re.search(r"logging\s*\{\s*log_bucket\s*=\s*var\.storage_log_bucket_name", storage, re.DOTALL)
    assert 'log_object_prefix = "access/${var.environment}/"' in storage
    assert re.search(r"logging\s*\{\s*log_bucket\s*=\s*var\.storage_log_bucket_name", bootstrap, re.DOTALL)
    assert 'log_object_prefix = "terraform-state/${var.environment}/"' in bootstrap


def test_test_root_uses_fictional_log_and_kms_values():
    test_variables = (TEST_ROOT / "variables.tf").read_text(encoding="utf-8")
    test_main = (TEST_ROOT / "main.tf").read_text(encoding="utf-8")

    for name in ("storage_log_bucket_name", "artifact_registry_kms_key_name"):
        assert f'variable "{name}"' in test_variables
        assert "fixture" in variable_block(test_variables, name)
        assert re.search(rf"{name}\s*=\s*var\.{name}", test_main)


def test_sql_is_postgres_17_private_and_protected():
    sql = read("sql.tf")
    assert 'database_version = "POSTGRES_17"' in sql
    assert re.search(r'edition\s*=\s*"ENTERPRISE"', sql)
    assert "ipv4_enabled    = false" in sql
    assert 'availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"' in sql
    assert 'deletion_protection = var.environment == "production"' in sql
    assert "point_in_time_recovery_enabled = true" in sql
    assert "disk_autoresize = true" in sql
    assert 'name  = "cloudsql.enable_pgaudit"' in sql
    assert 'name  = "pgaudit.log"' in sql
    assert 'value = "ddl,role,write"' in sql


def test_network_has_flow_logs_and_explicit_default_deny():
    network = read("network.tf")
    assert 'metadata             = "INCLUDE_ALL_METADATA"' in network
    assert 'resource "google_compute_firewall" "default_deny_ingress"' in network
    assert 'direction = "INGRESS"' in network
    assert re.search(r'deny\s*\{\s*protocol\s*=\s*"all"', network, re.DOTALL)


def test_artifact_repository_uses_external_cmek():
    serverless = read("serverless.tf")
    assert "kms_key_name  = var.artifact_registry_kms_key_name" in serverless


def test_state_recovery_does_not_block_backend_rewrites():
    bootstrap = (ROOT / "infra" / "terraform" / "bootstrap" / "state" / "main.tf").read_text(encoding="utf-8")
    assert "soft_delete_policy" in bootstrap
    assert "retention_policy" not in bootstrap


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
    assert 'role = "roles/viewer"' not in identities
    assert 'role = "roles/iam.serviceAccountAdmin"' not in identities
    assert 'resource "google_project_iam_custom_role" "terraform_plan_readonly"' in identities
    assert 'resource "google_project_iam_custom_role" "terraform_apply_service_accounts"' in identities
    assert "assertion.sub == 'repo:${var.github_repository}:environment:${var.wif_trust[each.key].github_environment}'" in identities
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
