output "api_service_account_email" { value = google_service_account.identities["api"].email }
output "worker_service_account_email" { value = google_service_account.identities["worker"].email }
output "task_invoker_service_account_email" { value = google_service_account.identities["task_invoker"].email }
output "migration_service_account_email" { value = google_service_account.identities["migration"].email }
output "bootstrap_service_account_email" { value = google_service_account.identities["bootstrap"].email }

output "terraform_plan_service_account_email" { value = google_service_account.identities["terraform_plan"].email }
output "terraform_apply_service_account_email" { value = google_service_account.identities["terraform_apply"].email }
output "deploy_service_account_email" { value = google_service_account.identities["deploy"].email }
output "rollback_service_account_email" { value = google_service_account.identities["rollback"].email }
output "admin_bootstrap_service_account_email" { value = google_service_account.identities["admin_bootstrap"].email }
output "access_release_service_account_email" { value = try(google_service_account.identities["access_release"].email, null) }

output "terraform_plan_wif_provider_name" { value = google_iam_workload_identity_pool_provider.workflow["terraform-plan"].name }
output "terraform_apply_wif_provider_name" { value = google_iam_workload_identity_pool_provider.workflow["terraform-apply"].name }
output "deploy_wif_provider_name" { value = google_iam_workload_identity_pool_provider.workflow["deploy"].name }
output "rollback_wif_provider_name" { value = google_iam_workload_identity_pool_provider.workflow["rollback"].name }
output "admin_bootstrap_wif_provider_name" { value = google_iam_workload_identity_pool_provider.workflow["admin-bootstrap"].name }
output "access_release_wif_provider_name" { value = try(google_iam_workload_identity_pool_provider.workflow["access-release"].name, null) }

output "network_id" { value = google_compute_network.access.id }
output "private_subnet_id" { value = google_compute_subnetwork.private.id }
output "database_instance_connection_name" { value = google_sql_database_instance.postgres.connection_name }
output "database_private_ip" { value = google_sql_database_instance.postgres.private_ip_address }
output "database_name" { value = google_sql_database.application.name }
output "secret_resource_ids" { value = { for name, secret in google_secret_manager_secret.containers : name => secret.id } }
output "services_ready" { value = terraform_data.services_ready.output }

# Native tests consume only this non-secret, resource-derived contract. It is
# not a runtime/client interface. Every IAM/secret metric comes from the full
# actual Terraform resource collection, never a manually selected subset.
output "terraform_test_contract" {
  value = {
    database = {
      postgres_17        = google_sql_database_instance.postgres.database_version == "POSTGRES_17"
      availability_type  = google_sql_database_instance.postgres.settings[0].availability_type
      deletion_protected = google_sql_database_instance.postgres.deletion_protection
    }
    service_accounts = {
      count                     = length(google_service_account.identities)
      distinct_account_id_count = length(toset([for account in values(google_service_account.identities) : account.account_id]))
      id_lengths                = [for account in values(google_service_account.identities) : length(account.account_id)]
    }
    wif = {
      provider_count                  = length(google_iam_workload_identity_pool_provider.workflow)
      distinct_provider_id_count      = length(toset([for provider in values(google_iam_workload_identity_pool_provider.workflow) : provider.workload_identity_pool_provider_id]))
      provider_id_lengths             = [for provider in values(google_iam_workload_identity_pool_provider.workflow) : length(provider.workload_identity_pool_provider_id)]
      pool_id_length                  = length(google_iam_workload_identity_pool.workflow.workload_identity_pool_id)
      impersonation_binding_count     = length(google_service_account_iam_member.workflow_impersonation)
      provider_specific_binding_count = length(google_service_account_iam_member.workflow_impersonation)
      provider_ids_by_identity        = { for identity, provider in google_iam_workload_identity_pool_provider.workflow : identity => provider.workload_identity_pool_provider_id }
      impersonation_roles_by_identity = { for identity, binding in google_service_account_iam_member.workflow_impersonation : identity => binding.role }
      workflow_identity_mapping_count = length([for name, provider in google_iam_workload_identity_pool_provider.workflow : provider if provider.attribute_mapping["attribute.workflow_identity"] == format("%q", name)])
      direct_claim_condition_count    = length([for provider in values(google_iam_workload_identity_pool_provider.workflow) : provider if strcontains(provider.attribute_condition, "assertion.workflow_ref") || strcontains(provider.attribute_condition, "assertion.job_workflow_ref")])
    }
    secrets = {
      container_count          = length(google_secret_manager_secret.containers)
      names                    = sort([for secret in values(google_secret_manager_secret.containers) : secret.secret_id])
      version_count            = length(google_secret_manager_secret_version.managed)
      binding_count            = length(google_secret_manager_secret_iam_member.least_privilege)
      binding_roles            = sort([for binding in values(google_secret_manager_secret_iam_member.least_privilege) : binding.role])
      binding_keys             = sort(keys(google_secret_manager_secret_iam_member.least_privilege))
      update_grant_role        = google_secret_manager_secret_iam_member.least_privilege["api-client-update-grant-key"].role
      update_grant_api_only    = google_secret_manager_secret_iam_member.least_privilege["api-client-update-grant-key"].member == "serviceAccount:access-${var.environment == "production" ? "prod" : "test"}-api@${var.project_id}.iam.gserviceaccount.com"
      bootstrap_database_role  = google_secret_manager_secret_iam_member.least_privilege["bootstrap-database"].role
      bootstrap_pin_role       = google_secret_manager_secret_iam_member.least_privilege["bootstrap-initial-pin-adder"].role
      bootstrap_pin_adder_only = google_secret_manager_secret_iam_member.least_privilege["bootstrap-initial-pin-adder"].member == "serviceAccount:access-${var.environment == "production" ? "prod" : "test"}-bootstrap@${var.project_id}.iam.gserviceaccount.com"
      workflow_secret_access_count = length(flatten([
        for workflow in ["terraform_plan", "terraform_apply", "deploy", "rollback", "admin_bootstrap", "access_release"] : [
          for binding in values(google_secret_manager_secret_iam_member.least_privilege) : binding
          if binding.member == "serviceAccount:access-${var.environment == "production" ? "prod" : "test"}-${local.role_ids[workflow]}@${var.project_id}.iam.gserviceaccount.com"
        ]
      ]))
      api_accessor_count       = length([for binding in values(google_secret_manager_secret_iam_member.least_privilege) : binding if binding.member == "serviceAccount:access-${var.environment == "production" ? "prod" : "test"}-api@${var.project_id}.iam.gserviceaccount.com" && binding.role == "roles/secretmanager.secretAccessor"])
      worker_accessor_count    = length([for binding in values(google_secret_manager_secret_iam_member.least_privilege) : binding if binding.member == "serviceAccount:access-${var.environment == "production" ? "prod" : "test"}-worker@${var.project_id}.iam.gserviceaccount.com" && binding.role == "roles/secretmanager.secretAccessor"])
      migration_accessor_count = length([for binding in values(google_secret_manager_secret_iam_member.least_privilege) : binding if binding.member == "serviceAccount:access-${var.environment == "production" ? "prod" : "test"}-migration@${var.project_id}.iam.gserviceaccount.com" && binding.role == "roles/secretmanager.secretAccessor"])
      bootstrap_accessor_count = length([for binding in values(google_secret_manager_secret_iam_member.least_privilege) : binding if binding.member == "serviceAccount:access-${var.environment == "production" ? "prod" : "test"}-bootstrap@${var.project_id}.iam.gserviceaccount.com" && binding.role == "roles/secretmanager.secretAccessor"])
    }
    iam = {
      project_binding_count = length(google_project_iam_member.least_privilege)
      project_roles         = sort([for binding in values(google_project_iam_member.least_privilege) : binding.role])
      runtime_project_member_counts = {
        api             = length([for binding in values(google_project_iam_member.least_privilege) : binding if binding.member == "serviceAccount:access-${var.environment == "production" ? "prod" : "test"}-api@${var.project_id}.iam.gserviceaccount.com"])
        worker          = length([for binding in values(google_project_iam_member.least_privilege) : binding if binding.member == "serviceAccount:access-${var.environment == "production" ? "prod" : "test"}-worker@${var.project_id}.iam.gserviceaccount.com"])
        migration       = length([for binding in values(google_project_iam_member.least_privilege) : binding if binding.member == "serviceAccount:access-${var.environment == "production" ? "prod" : "test"}-migration@${var.project_id}.iam.gserviceaccount.com"])
        bootstrap       = length([for binding in values(google_project_iam_member.least_privilege) : binding if binding.member == "serviceAccount:access-${var.environment == "production" ? "prod" : "test"}-bootstrap@${var.project_id}.iam.gserviceaccount.com"])
        terraform_plan  = length([for binding in values(google_project_iam_member.least_privilege) : binding if binding.member == "serviceAccount:access-${var.environment == "production" ? "prod" : "test"}-tf-plan@${var.project_id}.iam.gserviceaccount.com"])
        terraform_apply = length([for binding in values(google_project_iam_member.least_privilege) : binding if binding.member == "serviceAccount:access-${var.environment == "production" ? "prod" : "test"}-tf-apply@${var.project_id}.iam.gserviceaccount.com"])
      }
      custom_role = {
        id          = google_project_iam_custom_role.terraform_apply_secret_containers.role_id
        permissions = sort(google_project_iam_custom_role.terraform_apply_secret_containers.permissions)
      }
      state_binding_count           = length(google_storage_bucket_iam_member.terraform_state)
      state_roles                   = sort([for binding in values(google_storage_bucket_iam_member.terraform_state) : binding.role])
      state_binding_keys            = sort(keys(google_storage_bucket_iam_member.terraform_state))
      state_plan_member_count       = length([for binding in values(google_storage_bucket_iam_member.terraform_state) : binding if binding.member == "serviceAccount:access-${var.environment == "production" ? "prod" : "test"}-tf-plan@${var.project_id}.iam.gserviceaccount.com"])
      state_apply_member_count      = length([for binding in values(google_storage_bucket_iam_member.terraform_state) : binding if binding.member == "serviceAccount:access-${var.environment == "production" ? "prod" : "test"}-tf-apply@${var.project_id}.iam.gserviceaccount.com"])
      service_account_binding_count = length(concat(values(google_service_account_iam_member.deploy_runtime_user), values(google_service_account_iam_member.workflow_impersonation)))
      service_account_roles         = sort(concat([for binding in values(google_service_account_iam_member.deploy_runtime_user) : binding.role], [for binding in values(google_service_account_iam_member.workflow_impersonation) : binding.role]))
      deploy_runtime_roles          = { for identity, binding in google_service_account_iam_member.deploy_runtime_user : identity => binding.role }
      deploy_runtime_member_count   = length([for binding in values(google_service_account_iam_member.deploy_runtime_user) : binding if binding.member == "serviceAccount:access-${var.environment == "production" ? "prod" : "test"}-deploy@${var.project_id}.iam.gserviceaccount.com"])
      workflow_impersonation_roles  = { for identity, binding in google_service_account_iam_member.workflow_impersonation : identity => binding.role }
    }
    bootstrap_environment     = var.wif_trust["admin-bootstrap"].github_environment
    workflow_claim_categories = { for name, trust in var.wif_trust : name => sort(tolist(trust.workflow_claims)) }
  }
}
