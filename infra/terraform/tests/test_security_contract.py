import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "infra" / "terraform" / "modules" / "access_platform"
TEST_ROOT = ROOT / "infra" / "terraform" / "environments" / "test"
PRODUCTION_ROOT = ROOT / "infra" / "terraform" / "environments" / "production"


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
    secrets = read("secrets.tf")
    assert 'resource "google_secret_manager_secret_version" "managed"' in secrets
    assert "for_each    = toset([])" in secrets
    assert "secret_data = null" in secrets
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
    assert 'roles/artifactregistry.writer' not in identities
    assert 'roles/run.admin' not in identities
    assert 'rollback_traffic' not in identities


def test_workflow_impersonation_is_scoped_to_exact_permitted_workflow_claims():
    identities = read("identities.tf")
    variables = read("variables.tf")
    outputs = read("outputs.tf")
    assert re.search(r"workflow_claims\s*=\s*set\(string\)", variables)
    assert '"attribute.job_workflow_ref"' not in identities
    assert '"attribute.workflow_ref"' not in identities
    assert 'for claim in sort(tolist(var.wif_trust[each.key].workflow_claims))' in identities
    assert 'for_each           = local.workflow_accounts' in identities
    assert '"attribute.workflow_identity" = "\\"${each.key}\\"' in identities
    assert 'attribute.workflow_identity/${each.key}' in identities
    assert 'attribute.repository/${var.github_repository}' not in identities
    assert 'google_iam_workload_identity_pool.workflow.name}/attribute.workflow_identity/${each.key}' in identities
    assert 'projects/${var.project_id}/locations/global/workloadIdentityPools/' not in identities
    assert 'output "terraform_test_contract"' in outputs
    assert 'distinct_account_id_count' in outputs
    assert 'distinct_provider_id_count' in outputs
    assert 'impersonation_binding_count' in outputs
    assert 'google_secret_manager_secret_iam_member.least_privilege' in outputs
    assert 'google_project_iam_member.least_privilege' in outputs
    assert 'google_service_account_iam_member.deploy_runtime_user' in outputs


def test_iam_members_reference_managed_identities_and_custom_role():
    identities = read("identities.tf")
    assert 'member   = google_service_account.identities[each.value.account].member' in identities
    assert 'member             = google_service_account.identities["deploy"].member' in identities
    assert 'role = google_project_iam_custom_role.terraform_apply_secret_containers.name' in identities
    assert 'member    = google_service_account.identities[each.value.account].member' in identities


def test_worker_alone_has_bounded_metric_emission():
    identities = read("identities.tf")
    outputs = read("outputs.tf")
    assert re.search(r'worker-metric-writer\s*=\s*\{ account = "worker", role = "roles/monitoring\.metricWriter" \}', identities)
    assert identities.count('roles/monitoring.metricWriter') == 1
    assert 'metric_writer_binding_count' in outputs
    assert 'metric_writer_relations' in outputs
    assert 'google_project_iam_member.least_privilege' in outputs


def test_workflow_claims_follow_top_level_and_reusable_boundaries():
    test_main = (TEST_ROOT / "main.tf").read_text(encoding="utf-8")
    production_main = (PRODUCTION_ROOT / "main.tf").read_text(encoding="utf-8")
    assert 'rollback-test.yml@refs/heads/main' in test_main
    assert 'deploy-test.yml@refs/heads/main' in test_main
    assert 'rollback-production.yml@refs/heads/main' in production_main
    assert 'deploy-production.yml@refs/heads/main' in production_main
    for text in (test_main, production_main):
        assert 'workflow_claim     =' not in text
        assert 'terraform-plan' in text
        assert 'workflow_claims    = toset(["workflow_ref", "job_workflow_ref"])' in text
        assert 'workflow_claims    = toset(["job_workflow_ref"])' in text
        assert text.count('workflow_claims    = toset(["workflow_ref"])') == 4


def test_wif_display_names_use_short_physical_environment_id():
    identities = read("identities.tf")
    assert re.search(r'display_name\s*=\s*"Access \$\{each\.value\.role_id\} \(\$\{local\.environment_id\}\)"', identities)
    assert 'WIF (${var.environment})' not in identities
    assert 'display_name = "Access ${each.key} (${var.environment})"' not in identities
    assert 'display_name = "Access ${each.value}"' in identities


def test_terraform_apply_never_receives_broad_secret_administration():
    identities = read("identities.tf")
    assert 'roles/secretmanager.admin' not in identities
    assert 'secretmanager.versions.access' not in identities
    assert 'secretmanager.versions.get' not in identities
    assert 'google_secret_manager_secret_iam_member' in identities


def test_terraform_state_iam_is_prefix_scoped_for_plan_and_apply():
    identities = read("identities.tf")
    module_variables = read("variables.tf")
    for root in (TEST_ROOT, PRODUCTION_ROOT):
        assert 'variable "state_bucket_name"' in (root / "variables.tf").read_text(encoding="utf-8")
        assert re.search(r"state_bucket_name\s*=\s*var\.state_bucket_name", (root / "main.tf").read_text(encoding="utf-8"))
    assert 'resource "google_storage_bucket_iam_member" "terraform_state"' in identities
    assert 'roles/storage.objectViewer' in identities
    assert 'roles/storage.objectAdmin' in identities
    assert 'objects/access/${var.environment}/' in identities
    assert 'resource.name == \\"projects/_/buckets/${var.state_bucket_name}\\"' in identities
    assert 'variable "state_bucket_name"' in module_variables


def test_identity_and_secret_resources_wait_for_required_apis():
    identities = read("identities.tf")
    secrets = read("secrets.tf")
    assert 'depends_on = [terraform_data.services_ready]' in identities
    assert 'depends_on = [terraform_data.services_ready]' in secrets


def test_bootstrap_and_update_grant_secrets_are_separated():
    identities = read("identities.tf")
    secrets = read("secrets.tf")
    assert '"initial-admin-pin"' in secrets
    assert '"client-update-grant-key"' in secrets
    assert 'resource "google_secret_manager_secret_iam_member" "least_privilege"' in identities
    assert 'bootstrap-initial-pin-adder' in identities
    assert 'api-client-update-grant-key' in identities
    assert 'roles/secretmanager.secretVersionAdder' in identities
    assert 'roles/secretmanager.secretAccessor' in identities
