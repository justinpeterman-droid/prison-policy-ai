locals {
  environment_id = var.environment == "production" ? "prod" : "test"

  role_ids = {
    api             = "api"
    worker          = "worker"
    task_invoker    = "task-invoker"
    migration       = "migration"
    bootstrap       = "bootstrap"
    terraform_plan  = "tf-plan"
    terraform_apply = "tf-apply"
    deploy          = "deploy"
    rollback        = "rollback"
    admin_bootstrap = "admin-bootstrap"
    access_release  = "release"
  }

  service_account_roles = {
    for logical_name, role_id in local.role_ids : logical_name => role_id
    if logical_name != "access_release" || var.enable_access_release_identity
  }

  workflow_accounts = merge({
    terraform-plan = {
      account = "terraform_plan"
      role_id = local.role_ids.terraform_plan
    }
    terraform-apply = {
      account = "terraform_apply"
      role_id = local.role_ids.terraform_apply
    }
    deploy = {
      account = "deploy"
      role_id = local.role_ids.deploy
    }
    rollback = {
      account = "rollback"
      role_id = local.role_ids.rollback
    }
    admin-bootstrap = {
      account = "admin_bootstrap"
      role_id = local.role_ids.admin_bootstrap
    }
    }, var.enable_access_release_identity ? {
    access-release = {
      account = "access_release"
      role_id = local.role_ids.access_release
    }
  } : {})

  # Every project-level binding is an instance of one collection. Keeping the
  # resource collection complete lets the native security contract inspect all
  # actual planned project IAM members rather than a selected subset.
  project_iam_bindings = {
    api-sql-client                          = { account = "api", role = "roles/cloudsql.client" }
    api-task-enqueuer                       = { account = "api", role = "roles/cloudtasks.enqueuer" }
    worker-sql-client                       = { account = "worker", role = "roles/cloudsql.client" }
    worker-metric-writer                    = { account = "worker", role = "roles/monitoring.metricWriter" }
    migration-sql-client                    = { account = "migration", role = "roles/cloudsql.client" }
    bootstrap-sql-client                    = { account = "bootstrap", role = "roles/cloudsql.client" }
    terraform-plan-viewer                   = { account = "terraform_plan", role = "roles/viewer" }
    terraform-plan-security-reviewer        = { account = "terraform_plan", role = "roles/iam.securityReviewer" }
    terraform-plan-secret-metadata          = { account = "terraform_plan", role = "roles/secretmanager.viewer" }
    terraform-apply-network-admin           = { account = "terraform_apply", role = "roles/compute.networkAdmin" }
    terraform-apply-service-networking      = { account = "terraform_apply", role = "roles/servicenetworking.networksAdmin" }
    terraform-apply-sql-admin               = { account = "terraform_apply", role = "roles/cloudsql.admin" }
    terraform-apply-secret-container-admin  = { account = "terraform_apply", role = google_project_iam_custom_role.terraform_apply_secret_containers.name }
    terraform-apply-service-account-admin   = { account = "terraform_apply", role = "roles/iam.serviceAccountAdmin" }
    terraform-apply-workload-identity-admin = { account = "terraform_apply", role = "roles/iam.workloadIdentityPoolAdmin" }
    terraform-apply-project-iam-admin       = { account = "terraform_apply", role = "roles/resourcemanager.projectIamAdmin" }
  }

  state_iam_bindings = {
    terraform-plan = {
      account     = "terraform_plan"
      role        = "roles/storage.objectViewer"
      title       = "AccessTerraformPlanState"
      description = "Read only this environment's Terraform state objects."
    }
    terraform-apply = {
      account     = "terraform_apply"
      role        = "roles/storage.objectAdmin"
      title       = "AccessTerraformApplyState"
      description = "Manage only this environment's Terraform state objects."
    }
  }

  secret_iam_bindings = {
    api-database                = { account = "api", secret_id = google_secret_manager_secret.containers["access-database-url"].id, role = "roles/secretmanager.secretAccessor" }
    api-identity-pepper         = { account = "api", secret_id = google_secret_manager_secret.containers["identity-hash-pepper"].id, role = "roles/secretmanager.secretAccessor" }
    api-cursor-key              = { account = "api", secret_id = google_secret_manager_secret.containers["cursor-signing-key"].id, role = "roles/secretmanager.secretAccessor" }
    api-client-update-grant-key = { account = "api", secret_id = google_secret_manager_secret.containers["client-update-grant-key"].id, role = "roles/secretmanager.secretAccessor" }
    api-legacy-access           = { account = "api", secret_id = google_secret_manager_secret.containers["legacy-access-code"].id, role = "roles/secretmanager.secretAccessor" }
    api-legacy-admin            = { account = "api", secret_id = google_secret_manager_secret.containers["legacy-admin-code"].id, role = "roles/secretmanager.secretAccessor" }
    api-feedback                = { account = "api", secret_id = google_secret_manager_secret.containers["github-feedback-token"].id, role = "roles/secretmanager.secretAccessor" }
    api-session                 = { account = "api", secret_id = google_secret_manager_secret.containers["flask-session-secret"].id, role = "roles/secretmanager.secretAccessor" }
    worker-database             = { account = "worker", secret_id = google_secret_manager_secret.containers["access-database-url"].id, role = "roles/secretmanager.secretAccessor" }
    migration-database          = { account = "migration", secret_id = google_secret_manager_secret.containers["access-database-url"].id, role = "roles/secretmanager.secretAccessor" }
    bootstrap-database          = { account = "bootstrap", secret_id = google_secret_manager_secret.containers["access-database-url"].id, role = "roles/secretmanager.secretAccessor" }
    bootstrap-initial-pin-adder = { account = "bootstrap", secret_id = google_secret_manager_secret.containers["initial-admin-pin"].id, role = "roles/secretmanager.secretVersionAdder" }
  }

}

resource "google_service_account" "identities" {
  for_each     = local.service_account_roles
  project      = var.project_id
  account_id   = "access-${local.environment_id}-${each.value}"
  display_name = "Access ${each.value}"
  depends_on   = [terraform_data.services_ready]
}

resource "google_project_iam_member" "least_privilege" {
  for_each = local.project_iam_bindings
  project  = var.project_id
  role     = each.value.role
  member   = google_service_account.identities[each.value.account].member
}

# The state bucket is external. These are the only state bindings, each
# conditionally restricted to its environment's exact Terraform state prefix.
resource "google_storage_bucket_iam_member" "terraform_state" {
  for_each = local.state_iam_bindings
  bucket   = var.state_bucket_name
  role     = each.value.role
  member   = google_service_account.identities[each.value.account].member

  condition {
    title       = each.value.title
    description = each.value.description
    expression  = "resource.name == \"projects/_/buckets/${var.state_bucket_name}\" || resource.name.startsWith(\"projects/_/buckets/${var.state_bucket_name}/objects/access/${var.environment}/\")"
  }

  depends_on = [terraform_data.services_ready]
}

resource "google_project_iam_custom_role" "terraform_apply_secret_containers" {
  project     = var.project_id
  role_id     = "accessSecretContainerAdmin"
  title       = "Access Secret Manager containers only"
  description = "Manage secret containers and their IAM without reading secret versions."
  permissions = [
    "secretmanager.secrets.create",
    "secretmanager.secrets.delete",
    "secretmanager.secrets.get",
    "secretmanager.secrets.getIamPolicy",
    "secretmanager.secrets.list",
    "secretmanager.secrets.setIamPolicy",
    "secretmanager.secrets.update",
  ]
  depends_on = [terraform_data.services_ready]
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
  depends_on = [terraform_data.services_ready]
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
  depends_on = [terraform_data.services_ready]
}

resource "google_project_iam_member" "terraform_apply_op04_infrastructure" {
  project    = var.project_id
  role       = google_project_iam_custom_role.terraform_apply_op04_infrastructure.name
  member     = google_service_account.identities["terraform_apply"].member
  depends_on = [google_project_iam_custom_role.terraform_apply_op04_infrastructure]
}


resource "google_service_account_iam_member" "deploy_runtime_user" {
  for_each = {
    api       = google_service_account.identities["api"].name
    worker    = google_service_account.identities["worker"].name
    migration = google_service_account.identities["migration"].name
  }
  service_account_id = each.value
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.identities["deploy"].member
}

resource "google_iam_workload_identity_pool" "workflow" {
  project                   = var.project_id
  workload_identity_pool_id = "access-${local.environment_id}-wif"
  display_name              = "Access GitHub WIF (${local.environment_id})"
  depends_on                = [terraform_data.services_ready]
}

resource "google_iam_workload_identity_pool_provider" "workflow" {
  for_each                           = local.workflow_accounts
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.workflow.workload_identity_pool_id
  workload_identity_pool_provider_id = each.value.role_id
  display_name                       = "Access ${each.value.role_id} (${local.environment_id})"

  # Standard GitHub claims are preserved and every provider carries a static,
  # provider-specific identity value. Workflow-path claims remain direct
  # condition checks, so a reusable-only claim is never required as an
  # attribute.
  attribute_mapping = {
    "google.subject"              = "assertion.sub"
    "attribute.repository"        = "assertion.repository"
    "attribute.ref"               = "assertion.ref"
    "attribute.environment"       = "assertion.environment"
    "attribute.workflow_identity" = "\"${each.key}\""
  }

  attribute_condition = "assertion.repository == \"${var.github_repository}\" && assertion.ref == \"${var.wif_trust[each.key].ref_pattern}\" && assertion.environment == \"${var.wif_trust[each.key].github_environment}\" && (${join(" || ", [for claim in sort(tolist(var.wif_trust[each.key].workflow_claims)) : "has(assertion.${claim}) && assertion.${claim} in [${join(", ", [for ref in sort(tolist(var.wif_trust[each.key].workflow_refs)) : format("%q", ref)])}"])})"

  oidc { issuer_uri = "https://token.actions.githubusercontent.com" }
}

resource "google_service_account_iam_member" "workflow_impersonation" {
  for_each           = local.workflow_accounts
  service_account_id = google_service_account.identities[each.value.account].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.workflow.name}/attribute.workflow_identity/${each.key}"
}

# Per-secret members are one complete collection. No workflow identity is a
# member of this collection, so WIF accounts never receive secret payload access.
resource "google_secret_manager_secret_iam_member" "least_privilege" {
  for_each  = local.secret_iam_bindings
  secret_id = each.value.secret_id
  role      = each.value.role
  member    = google_service_account.identities[each.value.account].member
}
