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
output "access_release_service_account_email" {
  value = try(google_service_account.identities["access_release"].email, null)
}

output "terraform_plan_wif_provider_name" {
  value = google_iam_workload_identity_pool_provider.workflow["terraform-plan"].name
}
output "terraform_apply_wif_provider_name" {
  value = google_iam_workload_identity_pool_provider.workflow["terraform-apply"].name
}
output "deploy_wif_provider_name" {
  value = google_iam_workload_identity_pool_provider.workflow["deploy"].name
}
output "rollback_wif_provider_name" {
  value = google_iam_workload_identity_pool_provider.workflow["rollback"].name
}
output "admin_bootstrap_wif_provider_name" {
  value = google_iam_workload_identity_pool_provider.workflow["admin-bootstrap"].name
}
output "access_release_wif_provider_name" {
  value = try(google_iam_workload_identity_pool_provider.workflow["access-release"].name, null)
}

output "network_id" { value = google_compute_network.access.id }
output "private_subnet_id" { value = google_compute_subnetwork.private.id }
output "database_instance_connection_name" { value = google_sql_database_instance.postgres.connection_name }
output "database_private_ip" { value = google_sql_database_instance.postgres.private_ip_address }
output "database_name" { value = google_sql_database.application.name }
output "secret_resource_ids" {
  value = {
    access-database-url     = google_secret_manager_secret.access_database_url.id
    identity-hash-pepper    = google_secret_manager_secret.identity_hash_pepper.id
    cursor-signing-key      = google_secret_manager_secret.cursor_signing_key.id
    client-update-grant-key = google_secret_manager_secret.client_update_grant_key.id
    legacy-access-code      = google_secret_manager_secret.legacy_access_code.id
    legacy-admin-code       = google_secret_manager_secret.legacy_admin_code.id
    github-feedback-token   = google_secret_manager_secret.github_feedback_token.id
    flask-session-secret    = google_secret_manager_secret.flask_session_secret.id
    initial-admin-pin       = google_secret_manager_secret.initial_admin_pin.id
  }
}

output "services_ready" { value = terraform_data.services_ready.output }

# Native tests consume only this non-secret, resource-derived contract. It is
# not a runtime/client interface.
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
      provider_ids_by_identity = {
        for identity, provider in google_iam_workload_identity_pool_provider.workflow : identity => provider.workload_identity_pool_provider_id
      }
      impersonation_roles_by_identity = {
        for identity, binding in google_service_account_iam_member.workflow_impersonation : identity => binding.role
      }
      workflow_identity_mapping_count = length([
        for name, provider in google_iam_workload_identity_pool_provider.workflow : provider
        if provider.attribute_mapping["attribute.workflow_identity"] == format("%q", name)
      ])
      direct_claim_condition_count = length([
        for provider in values(google_iam_workload_identity_pool_provider.workflow) : provider
        if strcontains(provider.attribute_condition, "assertion.workflow_ref") || strcontains(provider.attribute_condition, "assertion.job_workflow_ref")
      ])
    }
    secrets = {
      container_count = length([
        google_secret_manager_secret.access_database_url,
        google_secret_manager_secret.identity_hash_pepper,
        google_secret_manager_secret.cursor_signing_key,
        google_secret_manager_secret.client_update_grant_key,
        google_secret_manager_secret.legacy_access_code,
        google_secret_manager_secret.legacy_admin_code,
        google_secret_manager_secret.github_feedback_token,
        google_secret_manager_secret.flask_session_secret,
        google_secret_manager_secret.initial_admin_pin,
      ])
      names = sort([
        google_secret_manager_secret.access_database_url.secret_id,
        google_secret_manager_secret.identity_hash_pepper.secret_id,
        google_secret_manager_secret.cursor_signing_key.secret_id,
        google_secret_manager_secret.client_update_grant_key.secret_id,
        google_secret_manager_secret.legacy_access_code.secret_id,
        google_secret_manager_secret.legacy_admin_code.secret_id,
        google_secret_manager_secret.github_feedback_token.secret_id,
        google_secret_manager_secret.flask_session_secret.secret_id,
        google_secret_manager_secret.initial_admin_pin.secret_id,
      ])
      binding_count = length([
        google_secret_manager_secret_iam_member.api_database,
        google_secret_manager_secret_iam_member.api_identity_pepper,
        google_secret_manager_secret_iam_member.api_cursor_key,
        google_secret_manager_secret_iam_member.api_client_update_grant_key,
        google_secret_manager_secret_iam_member.api_legacy_access,
        google_secret_manager_secret_iam_member.api_legacy_admin,
        google_secret_manager_secret_iam_member.api_feedback,
        google_secret_manager_secret_iam_member.api_session,
        google_secret_manager_secret_iam_member.worker_database,
        google_secret_manager_secret_iam_member.migration_database,
        google_secret_manager_secret_iam_member.bootstrap_database,
        google_secret_manager_secret_iam_member.bootstrap_initial_pin_adder,
      ])
      binding_roles = sort([
        google_secret_manager_secret_iam_member.api_database.role,
        google_secret_manager_secret_iam_member.api_identity_pepper.role,
        google_secret_manager_secret_iam_member.api_cursor_key.role,
        google_secret_manager_secret_iam_member.api_client_update_grant_key.role,
        google_secret_manager_secret_iam_member.api_legacy_access.role,
        google_secret_manager_secret_iam_member.api_legacy_admin.role,
        google_secret_manager_secret_iam_member.api_feedback.role,
        google_secret_manager_secret_iam_member.api_session.role,
        google_secret_manager_secret_iam_member.worker_database.role,
        google_secret_manager_secret_iam_member.migration_database.role,
        google_secret_manager_secret_iam_member.bootstrap_database.role,
        google_secret_manager_secret_iam_member.bootstrap_initial_pin_adder.role,
      ])
      update_grant = {
        role = google_secret_manager_secret_iam_member.api_client_update_grant_key.role
      }
      bootstrap = {
        database_role = google_secret_manager_secret_iam_member.bootstrap_database.role
        pin_role      = google_secret_manager_secret_iam_member.bootstrap_initial_pin_adder.role
      }
    }
    iam = {
      project_binding_count = length([
        google_project_iam_member.api_sql_client,
        google_project_iam_member.api_task_enqueuer,
        google_project_iam_member.worker_sql_client,
        google_project_iam_member.migration_sql_client,
        google_project_iam_member.bootstrap_sql_client,
        google_project_iam_member.terraform_plan_viewer,
        google_project_iam_member.terraform_plan_security_reviewer,
        google_project_iam_member.terraform_plan_secret_metadata,
        google_project_iam_member.terraform_apply_network_admin,
        google_project_iam_member.terraform_apply_service_networking,
        google_project_iam_member.terraform_apply_sql_admin,
        google_project_iam_member.terraform_apply_secret_container_admin,
        google_project_iam_member.terraform_apply_service_account_admin,
        google_project_iam_member.terraform_apply_workload_identity_admin,
        google_project_iam_member.terraform_apply_project_iam_admin,
      ])
      known_project_roles = sort([
        google_project_iam_member.api_sql_client.role,
        google_project_iam_member.api_task_enqueuer.role,
        google_project_iam_member.worker_sql_client.role,
        google_project_iam_member.migration_sql_client.role,
        google_project_iam_member.bootstrap_sql_client.role,
        google_project_iam_member.terraform_plan_viewer.role,
        google_project_iam_member.terraform_plan_security_reviewer.role,
        google_project_iam_member.terraform_plan_secret_metadata.role,
        google_project_iam_member.terraform_apply_network_admin.role,
        google_project_iam_member.terraform_apply_service_networking.role,
        google_project_iam_member.terraform_apply_sql_admin.role,
        google_project_iam_member.terraform_apply_service_account_admin.role,
        google_project_iam_member.terraform_apply_workload_identity_admin.role,
        google_project_iam_member.terraform_apply_project_iam_admin.role,
      ])
      custom_role = {
        id          = google_project_iam_custom_role.terraform_apply_secret_containers.role_id
        permissions = sort(google_project_iam_custom_role.terraform_apply_secret_containers.permissions)
      }
      state_binding_count = length([
        google_storage_bucket_iam_member.terraform_plan_state_read,
        google_storage_bucket_iam_member.terraform_apply_state_write,
      ])
      state_roles = sort([
        google_storage_bucket_iam_member.terraform_plan_state_read.role,
        google_storage_bucket_iam_member.terraform_apply_state_write.role,
      ])
      service_account_binding_count = length(concat(
        values(google_service_account_iam_member.deploy_runtime_user),
        values(google_service_account_iam_member.workflow_impersonation),
      ))
      service_account_roles = sort(concat(
        [for binding in values(google_service_account_iam_member.deploy_runtime_user) : binding.role],
        [for binding in values(google_service_account_iam_member.workflow_impersonation) : binding.role],
      ))
      deploy_runtime_roles = {
        for identity, binding in google_service_account_iam_member.deploy_runtime_user : identity => binding.role
      }
      workflow_impersonation_roles = {
        for identity, binding in google_service_account_iam_member.workflow_impersonation : identity => binding.role
      }
    }
    bootstrap_environment     = var.wif_trust["admin-bootstrap"].github_environment
    workflow_claim_categories = { for name, trust in var.wif_trust : name => sort(tolist(trust.workflow_claims)) }
  }
}
