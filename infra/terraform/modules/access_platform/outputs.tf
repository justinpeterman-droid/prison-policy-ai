output "api_service_account_email" {
  value = google_service_account.api.email
}

output "worker_service_account_email" {
  value = google_service_account.worker.email
}

output "task_invoker_service_account_email" {
  value = google_service_account.task_invoker.email
}

output "migration_service_account_email" {
  value = google_service_account.migration.email
}

output "bootstrap_service_account_email" {
  value = google_service_account.bootstrap.email
}

output "terraform_plan_service_account_email" {
  value = google_service_account.workflow["terraform-plan"].email
}

output "terraform_apply_service_account_email" {
  value = google_service_account.workflow["terraform-apply"].email
}

output "deploy_service_account_email" {
  value = google_service_account.workflow["deploy"].email
}

output "rollback_service_account_email" {
  value = google_service_account.workflow["rollback"].email
}

output "admin_bootstrap_service_account_email" {
  value = google_service_account.workflow["admin-bootstrap"].email
}

output "access_release_service_account_email" {
  value = try(google_service_account.workflow["access-release"].email, null)
}

output "terraform_plan_wif_provider_name" {
  value = google_iam_workload_identity_pool_provider.github["terraform-plan"].name
}

output "terraform_apply_wif_provider_name" {
  value = google_iam_workload_identity_pool_provider.github["terraform-apply"].name
}

output "deploy_wif_provider_name" {
  value = google_iam_workload_identity_pool_provider.github["deploy"].name
}

output "rollback_wif_provider_name" {
  value = google_iam_workload_identity_pool_provider.github["rollback"].name
}

output "admin_bootstrap_wif_provider_name" {
  value = google_iam_workload_identity_pool_provider.github["admin-bootstrap"].name
}

output "access_release_wif_provider_name" {
  value = try(google_iam_workload_identity_pool_provider.github["access-release"].name, null)
}

output "network_id" {
  value = google_compute_network.access.id
}

output "private_subnet_id" {
  value = google_compute_subnetwork.private.id
}

output "database_instance_connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}

output "database_private_ip" {
  value     = google_sql_database_instance.postgres.private_ip_address
  sensitive = true
}

output "database_name" {
  value = google_sql_database.application.name
}

output "secret_resource_ids" {
  value = {
    access_database_url     = google_secret_manager_secret.access_database_url.id
    identity_hash_pepper    = google_secret_manager_secret.identity_hash_pepper.id
    cursor_signing_key      = google_secret_manager_secret.cursor_signing_key.id
    client_update_grant_key = google_secret_manager_secret.client_update_grant_key.id
    legacy_access_code      = google_secret_manager_secret.legacy_access_code.id
    legacy_admin_code       = google_secret_manager_secret.legacy_admin_code.id
    github_feedback_token   = google_secret_manager_secret.github_feedback_token.id
    flask_session_secret    = google_secret_manager_secret.flask_session_secret.id
    initial_admin_pin       = google_secret_manager_secret.initial_admin_pin.id
  }
}
