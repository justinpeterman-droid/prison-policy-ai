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
      principal_set_category_count    = length([for identity, binding in google_service_account_iam_member.workflow_impersonation : binding if strcontains(binding.member, "/attribute.workflow_identity/${identity}")])
    }
    secrets = {
      container_count              = length(google_secret_manager_secret.containers)
      names                        = sort([for secret in values(google_secret_manager_secret.containers) : secret.secret_id])
      version_count                = length(google_secret_manager_secret_version.managed)
      binding_count                = length(google_secret_manager_secret_iam_member.least_privilege)
      binding_roles                = sort([for binding in values(google_secret_manager_secret_iam_member.least_privilege) : binding.role])
      binding_keys                 = sort(keys(google_secret_manager_secret_iam_member.least_privilege))
      update_grant_role            = google_secret_manager_secret_iam_member.least_privilege["api-client-update-grant-key"].role
      update_grant_api_only        = local.secret_iam_bindings["api-client-update-grant-key"].account == "api"
      bootstrap_database_role      = google_secret_manager_secret_iam_member.least_privilege["bootstrap-database"].role
      bootstrap_pin_role           = google_secret_manager_secret_iam_member.least_privilege["bootstrap-initial-pin-adder"].role
      bootstrap_pin_adder_only     = local.secret_iam_bindings["bootstrap-initial-pin-adder"].account == "bootstrap"
      workflow_secret_access_count = length([for binding in values(local.secret_iam_bindings) : binding if contains(["terraform_plan", "terraform_apply", "deploy", "rollback", "admin_bootstrap", "access_release"], binding.account)])
      api_accessor_count           = length([for binding in values(local.secret_iam_bindings) : binding if binding.account == "api" && binding.role == "roles/secretmanager.secretAccessor"])
      worker_accessor_count        = length([for binding in values(local.secret_iam_bindings) : binding if binding.account == "worker" && binding.role == "roles/secretmanager.secretAccessor"])
      migration_accessor_count     = length([for binding in values(local.secret_iam_bindings) : binding if binding.account == "migration" && binding.role == "roles/secretmanager.secretAccessor"])
      bootstrap_accessor_count     = length([for binding in values(local.secret_iam_bindings) : binding if binding.account == "bootstrap" && binding.role == "roles/secretmanager.secretAccessor"])
    }
    iam = {
      project_binding_count = length(google_project_iam_member.least_privilege)
      project_roles         = sort([for key, binding in local.project_iam_bindings : key == "terraform-apply-secret-container-admin" ? "projects/${var.project_id}/roles/${google_project_iam_custom_role.terraform_apply_secret_containers.role_id}" : binding.role])
      runtime_project_member_counts = {
        api             = length([for binding in values(local.project_iam_bindings) : binding if binding.account == "api"])
        worker          = length([for binding in values(local.project_iam_bindings) : binding if binding.account == "worker"])
        migration       = length([for binding in values(local.project_iam_bindings) : binding if binding.account == "migration"])
        bootstrap       = length([for binding in values(local.project_iam_bindings) : binding if binding.account == "bootstrap"])
        terraform_plan  = length([for binding in values(local.project_iam_bindings) : binding if binding.account == "terraform_plan"])
        terraform_apply = length([for binding in values(local.project_iam_bindings) : binding if binding.account == "terraform_apply"])
      }
      custom_role = {
        id          = google_project_iam_custom_role.terraform_apply_secret_containers.role_id
        permissions = sort(google_project_iam_custom_role.terraform_apply_secret_containers.permissions)
      }
      state_binding_count           = length(google_storage_bucket_iam_member.terraform_state)
      state_roles                   = sort([for binding in values(google_storage_bucket_iam_member.terraform_state) : binding.role])
      state_binding_keys            = sort(keys(google_storage_bucket_iam_member.terraform_state))
      state_plan_member_count       = length([for binding in values(local.state_iam_bindings) : binding if binding.account == "terraform_plan"])
      state_apply_member_count      = length([for binding in values(local.state_iam_bindings) : binding if binding.account == "terraform_apply"])
      service_account_binding_count = length(concat(values(google_service_account_iam_member.deploy_runtime_user), values(google_service_account_iam_member.workflow_impersonation)))
      service_account_roles         = sort(concat([for binding in values(google_service_account_iam_member.deploy_runtime_user) : binding.role], [for binding in values(google_service_account_iam_member.workflow_impersonation) : binding.role]))
      deploy_runtime_roles          = { for identity, binding in google_service_account_iam_member.deploy_runtime_user : identity => binding.role }
      deploy_runtime_member_count   = length(google_service_account_iam_member.deploy_runtime_user)
      workflow_impersonation_roles  = { for identity, binding in google_service_account_iam_member.workflow_impersonation : identity => binding.role }
    }
    bootstrap_environment     = var.wif_trust["admin-bootstrap"].github_environment
    workflow_claim_categories = { for name, trust in var.wif_trust : name => sort(tolist(trust.workflow_claims)) }
  }
}
