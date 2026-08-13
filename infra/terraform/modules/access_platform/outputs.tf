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
