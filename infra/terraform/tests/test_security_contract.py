import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "infra" / "terraform" / "modules" / "access_platform"
TEST_ROOT = ROOT / "infra" / "terraform" / "environments" / "test"
PRODUCTION_ROOT = ROOT / "infra" / "terraform" / "environments" / "production"


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


def resource_block(source: str, resource_type: str, name: str) -> str:
    match = re.search(
        rf'resource\s+"{re.escape(resource_type)}"\s+"{re.escape(name)}"\s*\{{',
        source,
    )
    assert match, f"missing resource {resource_type}.{name}"

    depth = 0
    for index in range(match.end() - 1, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start(): index + 1]
    raise AssertionError(f"unterminated resource {resource_type}.{name}")


def database_flag_value(source: str, name: str) -> str:
    match = re.search(
        rf'database_flags\s*\{{\s*name\s*=\s*"{re.escape(name)}"\s*value\s*=\s*"([^"]+)"\s*\}}',
        source,
        re.DOTALL,
    )
    assert match, f"missing database flag {name}"
    return match.group(1)


def test_pinned_checkov_contract_has_no_unresolved_hardening_categories():
    contract = (MODULE.parent.parent / "tests" / "access_platform.tftest.hcl").read_text(
        encoding="utf-8"
    )
    for token in (
        "storage_log_bucket_name",
        "artifact_registry_kms_key_name",
        "enable_flow_logs",
        "POSTGRES_18",
    ):
        assert token in contract


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


def test_sql_is_postgres_18_private_and_protected():
    sql = read("sql.tf")
    assert re.search(r'database_version\s*=\s*"POSTGRES_18"', sql)
    assert re.search(r"ipv4_enabled\s*=\s*false", sql)
    assert re.search(r'availability_type\s*=\s*var\.environment == "production" \? "REGIONAL" : "ZONAL"', sql)
    assert re.search(r'deletion_protection\s*=\s*var\.environment == "production"', sql)
    assert re.search(r"point_in_time_recovery_enabled\s*=\s*true", sql)
    assert re.search(r"disk_autoresize\s*=\s*true", sql)


def test_security_hardening_replaces_basic_and_sa_admin_project_roles():
    identities = read("identities.tf")
    assert 'role = "roles/viewer"' not in identities
    assert 'role = "roles/iam.serviceAccountAdmin"' not in identities
    assert 'resource "google_project_iam_custom_role" "terraform_plan_readonly"' in identities
    assert 'role = google_project_iam_custom_role.terraform_plan_readonly.name' in identities
    assert 'resource "google_project_iam_custom_role" "terraform_apply_service_accounts"' in identities
    assert 'role = google_project_iam_custom_role.terraform_apply_service_accounts.name' in identities


def test_plan_custom_role_excludes_unmanaged_or_duplicate_read_categories():
    role = resource_block(
        read("identities.tf"),
        "google_project_iam_custom_role",
        "terraform_plan_readonly",
    )
    for permission in (
        "cloudscheduler.jobs.getIamPolicy",
        "compute.addresses.get",
        "compute.addresses.list",
        "compute.backendServices.getIamPolicy",
        "compute.forwardingRules.get",
        "compute.forwardingRules.list",
        "compute.networks.getEffectiveFirewalls",
        "compute.securityPolicies.getIamPolicy",
        "vpcaccess.connectors.get",
        "vpcaccess.connectors.list",
        "workflows.workflows.getIamPolicy",
    ):
        assert f'"{permission}"' not in role

    for permission in (
        "compute.regionNetworkEndpointGroups.get",
        "compute.regionNetworkEndpointGroups.list",
        "servicenetworking.services.get",
    ):
        assert f'"{permission}"' in role

    assert '"compute.networkEndpointGroups.get"' not in role
    assert '"compute.networkEndpointGroups.list"' not in role


def test_wif_subject_is_exact_for_each_approved_repository_environment_identity():
    identities = read("identities.tf")
    expected = (
        'assertion.sub == \\"repo:justinpeterman-droid/prison-policy-ai:environment:'
        '${var.wif_trust[each.key].github_environment}\\"'
    )
    assert expected in identities
    assert 'assertion.repository == \\"${var.github_repository}\\"' in identities
    assert 'assertion.ref == \\"${var.wif_trust[each.key].ref_pattern}\\"' in identities
    assert 'assertion.environment == \\"${var.wif_trust[each.key].github_environment}\\"' in identities


def test_wif_rejects_configured_repository_that_differs_from_approved_subject():
    provider = resource_block(
        read("identities.tf"),
        "google_iam_workload_identity_pool_provider",
        "workflow",
    )
    assert re.search(
        r"precondition\s*\{\s*condition\s*=\s*var\.github_repository\s*==\s*"
        r'"justinpeterman-droid/prison-policy-ai"',
        provider,
        re.DOTALL,
    )


def test_vpc_has_flow_logs_and_an_explicit_default_deny_ingress_firewall():
    network = read("network.tf")
    subnetwork = resource_block(network, "google_compute_subnetwork", "private")
    assert re.search(r"log_config\s*\{", subnetwork)
    assert 'aggregation_interval = "INTERVAL_5_SEC"' in subnetwork
    assert re.search(r"flow_sampling\s*=\s*0\.5", subnetwork)
    assert 'metadata             = "INCLUDE_ALL_METADATA"' in subnetwork

    firewall = resource_block(network, "google_compute_firewall", "default_deny_ingress")
    assert re.search(r'direction\s*=\s*"INGRESS"', firewall)
    assert re.search(r'priority\s*=\s*65534', firewall)
    assert re.search(r'deny\s*\{\s*protocol\s*=\s*"all"', firewall, re.DOTALL)
    assert re.search(r'source_ranges\s*=\s*\["0\.0\.0\.0/0"\]', firewall)
    assert re.search(r"network\s*=\s*google_compute_network\.access\.name", firewall)


def test_cloud_armor_denies_log4j_canary_before_existing_throttle_and_allow_rules():
    edge = read("edge.tf")
    policy = resource_block(edge, "google_compute_security_policy", "edge")
    assert "evaluatePreconfiguredWaf('cve-canary')" in policy
    assert re.search(
        r'action\s*=\s*"deny\(403\)".*?priority\s*=\s*100.*?preview\s*=\s*false',
        policy,
        re.DOTALL,
    )
    assert re.search(r'action\s*=\s*"throttle"\s*priority\s*=\s*1000', policy)
    assert re.search(r'action\s*=\s*"allow"\s*priority\s*=\s*2147483647', policy)


def test_artifact_registry_uses_required_external_kms_key():
    repository = resource_block(
        read("serverless.tf"),
        "google_artifact_registry_repository",
        "backend",
    )
    assert re.search(
        r"kms_key_name\s*=\s*var\.artifact_registry_kms_key_name",
        repository,
    )


def test_postgres_18_requires_client_certificates_and_audited_logging_flags():
    sql = read("sql.tf")
    instance = resource_block(sql, "google_sql_database_instance", "postgres")
    assert 'database_version    = "POSTGRES_18"' in instance
    assert 'ssl_mode        = "TRUSTED_CLIENT_CERTIFICATE_REQUIRED"' in instance

    expected_flags = {
        "cloudsql.enable_pgaudit": "on",
        "log_checkpoints": "on",
        "log_connections": "on",
        "log_disconnections": "on",
        "log_duration": "on",
        "log_hostname": "on",
        "log_lock_waits": "on",
        "log_min_duration_statement": "-1",
        "log_min_error_statement": "error",
        "log_min_messages": "warning",
        "log_statement": "ddl",
        "pgaudit.log": "ddl,role,write",
    }
    assert {name: database_flag_value(instance, name) for name in expected_flags} == expected_flags


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
    assert 'role = google_project_iam_custom_role.terraform_plan_readonly.name' in identities
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
