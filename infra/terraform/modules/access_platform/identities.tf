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
}

resource "google_service_account" "identities" {
  for_each     = local.service_account_roles
  project      = var.project_id
  account_id   = "access-${local.environment_id}-${each.value}"
  display_name = "Access ${each.key} (${var.environment})"
}

resource "google_project_iam_member" "api_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = google_service_account.identities["api"].member
}

resource "google_project_iam_member" "api_task_enqueuer" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = google_service_account.identities["api"].member
}

resource "google_project_iam_member" "worker_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = google_service_account.identities["worker"].member
}

resource "google_project_iam_member" "migration_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = google_service_account.identities["migration"].member
}

resource "google_project_iam_member" "bootstrap_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = google_service_account.identities["bootstrap"].member
}

resource "google_project_iam_member" "terraform_plan_viewer" {
  project = var.project_id
  role    = "roles/viewer"
  member  = google_service_account.identities["terraform_plan"].member
}

resource "google_project_iam_member" "terraform_plan_security_reviewer" {
  project = var.project_id
  role    = "roles/iam.securityReviewer"
  member  = google_service_account.identities["terraform_plan"].member
}

resource "google_project_iam_member" "terraform_plan_secret_metadata" {
  project = var.project_id
  role    = "roles/secretmanager.viewer"
  member  = google_service_account.identities["terraform_plan"].member
}

resource "google_project_iam_member" "terraform_apply_network_admin" {
  project = var.project_id
  role    = "roles/compute.networkAdmin"
  member  = google_service_account.identities["terraform_apply"].member
}

resource "google_project_iam_member" "terraform_apply_service_networking" {
  project = var.project_id
  role    = "roles/servicenetworking.networksAdmin"
  member  = google_service_account.identities["terraform_apply"].member
}

resource "google_project_iam_member" "terraform_apply_sql_admin" {
  project = var.project_id
  role    = "roles/cloudsql.admin"
  member  = google_service_account.identities["terraform_apply"].member
}

resource "google_project_iam_member" "terraform_apply_secret_admin" {
  project = var.project_id
  role    = "roles/secretmanager.admin"
  member  = google_service_account.identities["terraform_apply"].member
}

resource "google_project_iam_member" "terraform_apply_service_account_admin" {
  project = var.project_id
  role    = "roles/iam.serviceAccountAdmin"
  member  = google_service_account.identities["terraform_apply"].member
}

resource "google_project_iam_member" "terraform_apply_workload_identity_admin" {
  project = var.project_id
  role    = "roles/iam.workloadIdentityPoolAdmin"
  member  = google_service_account.identities["terraform_apply"].member
}

resource "google_project_iam_member" "terraform_apply_project_iam_admin" {
  project = var.project_id
  role    = "roles/resourcemanager.projectIamAdmin"
  member  = google_service_account.identities["terraform_apply"].member
}

resource "google_project_iam_member" "deploy_artifact_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = google_service_account.identities["deploy"].member
}

resource "google_project_iam_member" "deploy_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = google_service_account.identities["deploy"].member
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

resource "google_project_iam_custom_role" "rollback_traffic" {
  project     = var.project_id
  role_id     = "accessRollbackTraffic"
  title       = "Access rollback traffic only"
  description = "Traffic adjustment only; service IAM later narrows this role to the API and worker."
  permissions = [
    "run.services.get",
    "run.services.update",
    "run.operations.get",
    "run.revisions.get",
    "run.revisions.list",
  ]
}

resource "google_project_iam_member" "rollback_traffic" {
  project = var.project_id
  role    = google_project_iam_custom_role.rollback_traffic.name
  member  = google_service_account.identities["rollback"].member
}

resource "google_iam_workload_identity_pool" "workflow" {
  project                   = var.project_id
  workload_identity_pool_id = "access-${local.environment_id}-wif"
  display_name              = "Access GitHub trust (${var.environment})"
}

resource "google_iam_workload_identity_pool_provider" "workflow" {
  for_each                           = local.workflow_accounts
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.workflow.workload_identity_pool_id
  workload_identity_pool_provider_id = each.value.role_id
  display_name                       = "GitHub ${each.key} (${var.environment})"

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.repository"       = "assertion.repository"
    "attribute.ref"              = "assertion.ref"
    "attribute.environment"      = "assertion.environment"
    "attribute.job_workflow_ref" = "assertion.job_workflow_ref"
  }

  attribute_condition = "assertion.repository == \"${var.github_repository}\" && assertion.ref == \"${var.wif_trust[each.key].ref_pattern}\" && assertion.environment == \"${var.wif_trust[each.key].github_environment}\" && assertion.job_workflow_ref in [${join(", ", [for ref in sort(tolist(var.wif_trust[each.key].workflow_refs)) : format("%q", ref)])}]"

  oidc { issuer_uri = "https://token.actions.githubusercontent.com" }
}

resource "google_service_account_iam_member" "workflow_impersonation" {
  for_each           = local.workflow_accounts
  service_account_id = google_service_account.identities[each.value.account].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.workflow.name}/attribute.job_workflow_ref/${one(var.wif_trust[each.key].workflow_refs)}"
}

# Secrets are bound individually below. No workflow account appears in a
# secret binding: WIF identities never receive application-secret payload access.
resource "google_secret_manager_secret_iam_member" "api_database" {
  secret_id = google_secret_manager_secret.access_database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.identities["api"].member
}

resource "google_secret_manager_secret_iam_member" "api_identity_pepper" {
  secret_id = google_secret_manager_secret.identity_hash_pepper.id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.identities["api"].member
}

resource "google_secret_manager_secret_iam_member" "api_cursor_key" {
  secret_id = google_secret_manager_secret.cursor_signing_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.identities["api"].member
}

resource "google_secret_manager_secret_iam_member" "api_client_update_grant_key" {
  secret_id = google_secret_manager_secret.client_update_grant_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.identities["api"].member
}

resource "google_secret_manager_secret_iam_member" "api_legacy_access" {
  secret_id = google_secret_manager_secret.legacy_access_code.id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.identities["api"].member
}

resource "google_secret_manager_secret_iam_member" "api_legacy_admin" {
  secret_id = google_secret_manager_secret.legacy_admin_code.id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.identities["api"].member
}

resource "google_secret_manager_secret_iam_member" "api_feedback" {
  secret_id = google_secret_manager_secret.github_feedback_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.identities["api"].member
}

resource "google_secret_manager_secret_iam_member" "api_session" {
  secret_id = google_secret_manager_secret.flask_session_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.identities["api"].member
}

resource "google_secret_manager_secret_iam_member" "worker_database" {
  secret_id = google_secret_manager_secret.access_database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.identities["worker"].member
}

resource "google_secret_manager_secret_iam_member" "migration_database" {
  secret_id = google_secret_manager_secret.access_database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.identities["migration"].member
}

resource "google_secret_manager_secret_iam_member" "bootstrap_database" {
  secret_id = google_secret_manager_secret.access_database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.identities["bootstrap"].member
}

resource "google_secret_manager_secret_iam_member" "bootstrap_initial_pin_adder" {
  secret_id = google_secret_manager_secret.initial_admin_pin.id
  role      = "roles/secretmanager.secretVersionAdder"
  member    = google_service_account.identities["bootstrap"].member
}
