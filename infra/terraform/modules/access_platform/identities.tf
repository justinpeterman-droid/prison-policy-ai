locals {
  environment_id = var.environment == "production" ? "prod" : "test"

  workflow_role_ids = {
    terraform-plan  = "tf-plan"
    terraform-apply = "tf-apply"
    deploy          = "deploy"
    rollback        = "rollback"
    admin-bootstrap = "admin-bootstrap"
    access-release  = "release"
  }

  declared_role_ids = toset([
    "api",
    "worker",
    "task-invoker",
    "migration",
    "bootstrap",
    "tf-plan",
    "tf-apply",
    "deploy",
    "rollback",
    "admin-bootstrap",
    "release",
  ])

  enabled_workflow_role_ids = {
    for name, role_id in local.workflow_role_ids : name => role_id
    if name != "access-release" || var.enable_access_release_identity
  }

  workflow_bindings = merge([
    for workflow, role_id in local.enabled_workflow_role_ids : {
      for workflow_ref in var.wif_trust[workflow].workflow_refs :
      "${workflow}:${workflow_ref}" => {
        workflow       = workflow
        role_id        = role_id
        workflow_ref   = workflow_ref
        workflow_claim = var.wif_trust[workflow].workflow_claim
      }
    }
  ]...)

  terraform_plan_role = google_project_iam_custom_role.terraform_plan_readonly.name

  rollback_role = google_project_iam_custom_role.rollback_traffic.name
}

resource "google_service_account" "api" {
  project      = var.project_id
  account_id   = "access-${local.environment_id}-api"
  display_name = "Access ${var.environment} API runtime"
}

resource "google_service_account" "worker" {
  project      = var.project_id
  account_id   = "access-${local.environment_id}-worker"
  display_name = "Access ${var.environment} worker runtime"
}

resource "google_service_account" "task_invoker" {
  project      = var.project_id
  account_id   = "access-${local.environment_id}-task-invoker"
  display_name = "Access ${var.environment} task invoker"
}

resource "google_service_account" "migration" {
  project      = var.project_id
  account_id   = "access-${local.environment_id}-migration"
  display_name = "Access ${var.environment} migration runtime"
}

resource "google_service_account" "bootstrap" {
  project      = var.project_id
  account_id   = "access-${local.environment_id}-bootstrap"
  display_name = "Access ${var.environment} administrator bootstrap runtime"
}

resource "google_service_account" "workflow" {
  for_each = local.enabled_workflow_role_ids

  project      = var.project_id
  account_id   = "access-${local.environment_id}-${each.value}"
  display_name = "Access ${var.environment} ${each.key} workflow"
}

resource "google_project_iam_member" "runtime_cloud_sql" {
  for_each = {
    api       = google_service_account.api.member
    worker    = google_service_account.worker.member
    migration = google_service_account.migration.member
    bootstrap = google_service_account.bootstrap.member
  }

  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = each.value
}

resource "google_project_iam_member" "terraform_plan" {
  for_each = toset([
    "roles/iam.securityReviewer",
    "roles/secretmanager.viewer",
  ])

  project = var.project_id
  role    = each.value
  member  = google_service_account.workflow["terraform-plan"].member
}

resource "google_project_iam_custom_role" "terraform_plan_readonly" {
  project     = var.project_id
  role_id     = "access${title(local.environment_id)}TerraformPlanRead"
  title       = "Access ${var.environment} Terraform plan read only"
  description = "Read only the resource types managed by the Access platform Terraform module."
  permissions = [
    "artifactregistry.repositories.get", "artifactregistry.repositories.getIamPolicy", "artifactregistry.repositories.list",
    "cloudscheduler.jobs.get", "cloudscheduler.jobs.list",
    "cloudsql.databases.get", "cloudsql.databases.list", "cloudsql.instances.get", "cloudsql.instances.list", "cloudsql.operations.get", "cloudsql.operations.list",
    "cloudtasks.queues.get", "cloudtasks.queues.getIamPolicy", "cloudtasks.queues.list",
    "compute.backendServices.get", "compute.backendServices.list", "compute.firewalls.get", "compute.firewalls.list", "compute.globalAddresses.get", "compute.globalAddresses.list", "compute.globalForwardingRules.get", "compute.globalForwardingRules.list", "compute.networks.get", "compute.networks.list", "compute.regionNetworkEndpointGroups.get", "compute.regionNetworkEndpointGroups.list", "compute.securityPolicies.get", "compute.securityPolicies.list", "compute.sslCertificates.get", "compute.sslCertificates.list", "compute.subnetworks.get", "compute.subnetworks.list", "compute.targetHttpProxies.get", "compute.targetHttpProxies.list", "compute.targetHttpsProxies.get", "compute.targetHttpsProxies.list", "compute.urlMaps.get", "compute.urlMaps.list",
    "dns.managedZones.get", "dns.managedZones.list", "dns.resourceRecordSets.list",
    "logging.logMetrics.get", "logging.logMetrics.list",
    "monitoring.alertPolicies.get", "monitoring.alertPolicies.list", "monitoring.dashboards.get", "monitoring.dashboards.list", "monitoring.uptimeCheckConfigs.get", "monitoring.uptimeCheckConfigs.list",
    "resourcemanager.projects.get",
    "run.jobs.get", "run.jobs.getIamPolicy", "run.jobs.list", "run.services.get", "run.services.getIamPolicy", "run.services.list",
    "serviceusage.services.get", "serviceusage.services.list", "servicenetworking.services.get",
    "storage.buckets.get", "storage.buckets.getIamPolicy", "storage.buckets.list",
    "workflows.workflows.get", "workflows.workflows.list",
  ]
  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "terraform_plan_readonly" {
  project = var.project_id
  role    = google_project_iam_custom_role.terraform_plan_readonly.name
  member  = google_service_account.workflow["terraform-plan"].member
}

resource "google_project_iam_custom_role" "terraform_secret_admin" {
  project     = var.project_id
  role_id     = "access${title(local.environment_id)}TerraformSecrets"
  title       = "Access ${var.environment} Terraform secret metadata administrator"
  description = "Manage secret containers and IAM without reading secret payloads."
  permissions = [
    "resourcemanager.projects.get",
    "secretmanager.secrets.create",
    "secretmanager.secrets.delete",
    "secretmanager.secrets.get",
    "secretmanager.secrets.getIamPolicy",
    "secretmanager.secrets.list",
    "secretmanager.secrets.setIamPolicy",
    "secretmanager.secrets.update",
  ]
}

resource "google_project_iam_member" "terraform_apply" {
  for_each = toset([
    "roles/cloudsql.admin",
    "roles/compute.networkAdmin",
    "roles/iam.roleAdmin",
    "roles/iam.workloadIdentityPoolAdmin",
    "roles/resourcemanager.projectIamAdmin",
    "roles/servicenetworking.networksAdmin",
    "roles/serviceusage.serviceUsageAdmin",
  ])
  project = var.project_id
  role    = each.value
  member  = google_service_account.workflow["terraform-apply"].member
}

resource "google_project_iam_custom_role" "terraform_apply_service_accounts" {
  project     = var.project_id
  role_id     = "access${title(local.environment_id)}ServiceAccountLifecycle"
  title       = "Access ${var.environment} service account lifecycle"
  description = "Create, update, delete, and bind managed service accounts without minting keys or credentials."
  permissions = [
    "iam.serviceAccounts.create",
    "iam.serviceAccounts.delete",
    "iam.serviceAccounts.get",
    "iam.serviceAccounts.getIamPolicy",
    "iam.serviceAccounts.list",
    "iam.serviceAccounts.setIamPolicy",
    "iam.serviceAccounts.update",
  ]
  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "terraform_apply_service_accounts" {
  project = var.project_id
  role    = google_project_iam_custom_role.terraform_apply_service_accounts.name
  member  = google_service_account.workflow["terraform-apply"].member
}

resource "google_project_iam_custom_role" "deploy_revision" {
  project     = var.project_id
  role_id     = "accessDeployRevision"
  title       = "Access deployment revisions only"
  description = "Deploy reviewed Cloud Run revisions without administering services."
  permissions = [
    "run.operations.get",
    "run.revisions.get",
    "run.revisions.list",
    "run.services.get",
    "run.services.update",
  ]
  depends_on = [google_project_service.required]
}

# First apply requires an authorized external bootstrap grant; Terraform cannot
# create or grant the management role before it already has that authority.
resource "google_project_iam_custom_role" "terraform_apply_op04_infrastructure" {
  project     = var.project_id
  role_id     = "accessOp04Infrastructure"
  title       = "Access OP04 infrastructure control plane"
  description = "Manage OP04 configuration and IAM only; no data-plane operations."
  permissions = [
    "artifactregistry.repositories.create", "artifactregistry.repositories.delete", "artifactregistry.repositories.get", "artifactregistry.repositories.getIamPolicy", "artifactregistry.repositories.list", "artifactregistry.repositories.setIamPolicy", "artifactregistry.repositories.update",
    "cloudtasks.queues.create", "cloudtasks.queues.delete", "cloudtasks.queues.get", "cloudtasks.queues.getIamPolicy", "cloudtasks.queues.list", "cloudtasks.queues.setIamPolicy", "cloudtasks.queues.update",
    "storage.buckets.create", "storage.buckets.delete", "storage.buckets.get", "storage.buckets.getIamPolicy", "storage.buckets.list", "storage.buckets.setIamPolicy", "storage.buckets.update",
    "dns.changes.create", "dns.changes.get", "dns.changes.list", "dns.managedZones.get", "dns.resourceRecordSets.create", "dns.resourceRecordSets.delete", "dns.resourceRecordSets.list",
    "compute.addresses.create", "compute.addresses.delete", "compute.addresses.get", "compute.backendServices.create", "compute.backendServices.delete", "compute.backendServices.get", "compute.backendServices.update", "compute.globalAddresses.create", "compute.globalAddresses.delete", "compute.globalAddresses.get", "compute.globalForwardingRules.create", "compute.globalForwardingRules.delete", "compute.globalForwardingRules.get", "compute.networkEndpointGroups.create", "compute.networkEndpointGroups.delete", "compute.networkEndpointGroups.get", "compute.securityPolicies.create", "compute.securityPolicies.delete", "compute.securityPolicies.get", "compute.securityPolicies.update", "compute.sslCertificates.create", "compute.sslCertificates.delete", "compute.sslCertificates.get", "compute.targetHttpProxies.create", "compute.targetHttpProxies.delete", "compute.targetHttpProxies.get", "compute.targetHttpsProxies.create", "compute.targetHttpsProxies.delete", "compute.targetHttpsProxies.get", "compute.urlMaps.create", "compute.urlMaps.delete", "compute.urlMaps.get", "compute.urlMaps.update",
    "iam.roles.create", "iam.roles.delete", "iam.roles.get", "iam.roles.update",
    "run.operations.get", "run.services.create", "run.services.delete", "run.services.get", "run.services.getIamPolicy", "run.services.list", "run.services.setIamPolicy", "run.services.update",
  ]
  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "terraform_apply_op04_infrastructure" {
  project    = var.project_id
  role       = google_project_iam_custom_role.terraform_apply_op04_infrastructure.name
  member     = google_service_account.workflow["terraform-apply"].member
  depends_on = [google_project_iam_custom_role.terraform_apply_op04_infrastructure]
}

resource "google_project_iam_member" "terraform_apply_secret_metadata" {
  project = var.project_id
  role    = google_project_iam_custom_role.terraform_secret_admin.name
  member  = google_service_account.workflow["terraform-apply"].member
}

resource "google_storage_bucket_iam_member" "terraform_plan_state" {
  bucket = var.state_bucket_name
  role   = "roles/storage.objectViewer"
  member = google_service_account.workflow["terraform-plan"].member

  condition {
    title       = "access_${local.environment_id}_state_read"
    description = "Read only this environment's Terraform state prefix."
    expression  = "resource.name.startsWith('projects/_/buckets/${var.state_bucket_name}/objects/access/${var.environment}/')"
  }
}

resource "google_storage_bucket_iam_member" "terraform_apply_state" {
  bucket = var.state_bucket_name
  role   = "roles/storage.objectAdmin"
  member = google_service_account.workflow["terraform-apply"].member

  condition {
    title       = "access_${local.environment_id}_state_write"
    description = "Read and write only this environment's Terraform state prefix."
    expression  = "resource.name.startsWith('projects/_/buckets/${var.state_bucket_name}/objects/access/${var.environment}/')"
  }
}

resource "google_project_iam_custom_role" "rollback_traffic" {
  project     = var.project_id
  role_id     = "access${title(local.environment_id)}RollbackTraffic"
  title       = "Access ${var.environment} rollback traffic"
  description = "Inspect revisions and move Cloud Run traffic without deploying artifacts."
  permissions = [
    "run.operations.get",
    "run.revisions.get",
    "run.revisions.list",
    "run.services.get",
    "run.services.update",
  ]
}

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = "access-${local.environment_id}-wif"
  display_name              = "Access ${var.environment} GitHub workflows"
  description               = "Environment-scoped GitHub OIDC trust."

  depends_on = [google_project_service.required]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  for_each = local.enabled_workflow_role_ids

  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = each.value
  display_name                       = "Access ${var.environment} ${each.key}"

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.repository"       = "assertion.repository"
    "attribute.ref"              = "assertion.ref"
    "attribute.environment"      = "assertion.environment"
    "attribute.workflow_ref"     = "assertion.workflow_ref"
    "attribute.job_workflow_ref" = "assertion.job_workflow_ref"
  }

  attribute_condition = <<-EOT
    assertion.sub == 'repo:${var.github_repository}:environment:${var.wif_trust[each.key].github_environment}' &&
    assertion.repository == '${var.github_repository}' &&
    assertion.ref == '${var.wif_trust[each.key].ref_pattern}' &&
    assertion.environment == '${var.wif_trust[each.key].github_environment}' &&
    assertion.${var.wif_trust[each.key].workflow_claim} in [${join(", ", [for workflow_ref in sort(tolist(var.wif_trust[each.key].workflow_refs)) : "'${workflow_ref}'"])}]
  EOT

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "workflow_wif" {
  for_each = local.workflow_bindings

  service_account_id = google_service_account.workflow[each.value.workflow].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.${each.value.workflow_claim}/${each.value.workflow_ref}"
}

resource "google_secret_manager_secret_iam_member" "api_database" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.access_database_url.id

  role = "roles/secretmanager.secretAccessor"

  member = google_service_account.api.member
}

resource "google_secret_manager_secret_iam_member" "worker_database" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.access_database_url.id

  role = "roles/secretmanager.secretAccessor"

  member = google_service_account.worker.member
}

resource "google_secret_manager_secret_iam_member" "migration_database" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.access_database_url.id

  role = "roles/secretmanager.secretAccessor"

  member = google_service_account.migration.member
}

resource "google_secret_manager_secret_iam_member" "bootstrap_database" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.access_database_url.id

  role = "roles/secretmanager.secretAccessor"

  member = google_service_account.bootstrap.member
}

resource "google_secret_manager_secret_iam_member" "api_identity_hash_pepper" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.identity_hash_pepper.id

  role = "roles/secretmanager.secretAccessor"

  member = google_service_account.api.member
}

resource "google_secret_manager_secret_iam_member" "api_cursor_signing_key" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.cursor_signing_key.id

  role = "roles/secretmanager.secretAccessor"

  member = google_service_account.api.member
}

resource "google_secret_manager_secret_iam_member" "api_client_update_grant_key" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.client_update_grant_key.id

  role = "roles/secretmanager.secretAccessor"

  member = google_service_account.api.member
}

resource "google_secret_manager_secret_iam_member" "api_legacy_access_code" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.legacy_access_code.id

  role = "roles/secretmanager.secretAccessor"

  member = google_service_account.api.member
}

resource "google_secret_manager_secret_iam_member" "api_legacy_admin_code" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.legacy_admin_code.id

  role = "roles/secretmanager.secretAccessor"

  member = google_service_account.api.member
}

resource "google_secret_manager_secret_iam_member" "api_github_feedback_token" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.github_feedback_token.id

  role = "roles/secretmanager.secretAccessor"

  member = google_service_account.api.member
}

resource "google_secret_manager_secret_iam_member" "api_flask_session_secret" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.flask_session_secret.id

  role = "roles/secretmanager.secretAccessor"

  member = google_service_account.api.member
}

resource "google_secret_manager_secret_iam_member" "bootstrap_initial_pin_adder" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.initial_admin_pin.id

  role = "roles/secretmanager.secretVersionAdder"

  member = google_service_account.bootstrap.member
}
