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
output "api_service_name" { value = google_cloud_run_v2_service.api.name }
output "worker_service_name" { value = google_cloud_run_v2_service.worker.name }
output "api_revision_uri" { value = google_cloud_run_v2_service.api.uri }
output "worker_uri" { value = google_cloud_run_v2_service.worker.uri }
output "queue_name" { value = google_cloud_tasks_queue.worker.name }
output "managed_hostname" { value = var.managed_hostname }
output "load_balancer_ip" { value = google_compute_global_address.api.address }
output "release_bucket_name" { value = google_storage_bucket.private["release"].name }
output "configuration_bucket_name" { value = google_storage_bucket.private["configuration"].name }
output "logical_backup_bucket_name" { value = google_storage_bucket.private["logical_backup"].name }
output "roster_bucket_name" { value = google_storage_bucket.private["roster"].name }
output "review_bucket_name" { value = google_storage_bucket.private["review"].name }

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
      principal_set_relations = {
        for identity, binding in google_service_account_iam_member.workflow_impersonation : identity => binding.member == "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.workflow.name}/attribute.workflow_identity/${identity}"
      }
    }
    secrets = {
      container_count = length(google_secret_manager_secret.containers)
      names           = sort([for secret in values(google_secret_manager_secret.containers) : secret.secret_id])
      version_count   = length(google_secret_manager_secret_version.managed)
      binding_count   = length(google_secret_manager_secret_iam_member.least_privilege)
      binding_roles   = sort([for binding in values(google_secret_manager_secret_iam_member.least_privilege) : binding.role])
      binding_keys    = sort(keys(google_secret_manager_secret_iam_member.least_privilege))
      exact_relations = {
        for key, binding in google_secret_manager_secret_iam_member.least_privilege : key => binding.role == (key == "bootstrap-initial-pin-adder" ? "roles/secretmanager.secretVersionAdder" : "roles/secretmanager.secretAccessor") && binding.member == google_service_account.identities[lookup({ api-database = "api", api-identity-pepper = "api", api-cursor-key = "api", api-client-update-grant-key = "api", api-legacy-access = "api", api-legacy-admin = "api", api-feedback = "api", api-session = "api", worker-database = "worker", migration-database = "migration", bootstrap-database = "bootstrap", bootstrap-initial-pin-adder = "bootstrap" }, key)].member && binding.secret_id == google_secret_manager_secret.containers[lookup({ api-database = "access-database-url", api-identity-pepper = "identity-hash-pepper", api-cursor-key = "cursor-signing-key", api-client-update-grant-key = "client-update-grant-key", api-legacy-access = "legacy-access-code", api-legacy-admin = "legacy-admin-code", api-feedback = "github-feedback-token", api-session = "flask-session-secret", worker-database = "access-database-url", migration-database = "access-database-url", bootstrap-database = "access-database-url", bootstrap-initial-pin-adder = "initial-admin-pin" }, key)].id
      }
    }
    iam = {
      project_binding_count = length(google_project_iam_member.least_privilege)
      project_roles         = sort([for key, binding in google_project_iam_member.least_privilege : key == "terraform-apply-secret-container-admin" ? "projects/${var.project_id}/roles/${google_project_iam_custom_role.terraform_apply_secret_containers.role_id}" : binding.role])
      exact_relations = {
        for key, binding in google_project_iam_member.least_privilege : key => binding.member == google_service_account.identities[lookup({ api-sql-client = "api", api-task-enqueuer = "api", worker-sql-client = "worker", migration-sql-client = "migration", bootstrap-sql-client = "bootstrap", terraform-plan-viewer = "terraform_plan", terraform-plan-security-reviewer = "terraform_plan", terraform-plan-secret-metadata = "terraform_plan", terraform-apply-network-admin = "terraform_apply", terraform-apply-service-networking = "terraform_apply", terraform-apply-sql-admin = "terraform_apply", terraform-apply-secret-container-admin = "terraform_apply", terraform-apply-service-account-admin = "terraform_apply", terraform-apply-workload-identity-admin = "terraform_apply", terraform-apply-project-iam-admin = "terraform_apply" }, key)].member && binding.role == (key == "terraform-apply-secret-container-admin" ? google_project_iam_custom_role.terraform_apply_secret_containers.name : lookup({ api-sql-client = "roles/cloudsql.client", api-task-enqueuer = "roles/cloudtasks.enqueuer", worker-sql-client = "roles/cloudsql.client", migration-sql-client = "roles/cloudsql.client", bootstrap-sql-client = "roles/cloudsql.client", terraform-plan-viewer = "roles/viewer", terraform-plan-security-reviewer = "roles/iam.securityReviewer", terraform-plan-secret-metadata = "roles/secretmanager.viewer", terraform-apply-network-admin = "roles/compute.networkAdmin", terraform-apply-service-networking = "roles/servicenetworking.networksAdmin", terraform-apply-sql-admin = "roles/cloudsql.admin", terraform-apply-service-account-admin = "roles/iam.serviceAccountAdmin", terraform-apply-workload-identity-admin = "roles/iam.workloadIdentityPoolAdmin", terraform-apply-project-iam-admin = "roles/resourcemanager.projectIamAdmin" }, key))
      }
      custom_role = {
        id          = google_project_iam_custom_role.terraform_apply_secret_containers.role_id
        permissions = sort(google_project_iam_custom_role.terraform_apply_secret_containers.permissions)
      }
      state_binding_count           = length(google_storage_bucket_iam_member.terraform_state)
      state_roles                   = sort([for binding in values(google_storage_bucket_iam_member.terraform_state) : binding.role])
      state_binding_keys            = sort(keys(google_storage_bucket_iam_member.terraform_state))
      exact_state_relations         = { for key, binding in google_storage_bucket_iam_member.terraform_state : key => binding.member == google_service_account.identities[key == "terraform-plan" ? "terraform_plan" : "terraform_apply"].member && binding.role == (key == "terraform-plan" ? "roles/storage.objectViewer" : "roles/storage.objectAdmin") }
      service_account_binding_count = length(concat(values(google_service_account_iam_member.deploy_runtime_user), values(google_service_account_iam_member.workflow_impersonation)))
      service_account_roles         = sort(concat([for binding in values(google_service_account_iam_member.deploy_runtime_user) : binding.role], [for binding in values(google_service_account_iam_member.workflow_impersonation) : binding.role]))
      deploy_runtime_roles          = { for identity, binding in google_service_account_iam_member.deploy_runtime_user : identity => binding.role }
      exact_deploy_relations        = { for key, binding in google_service_account_iam_member.deploy_runtime_user : key => binding.member == google_service_account.identities["deploy"].member && binding.role == "roles/iam.serviceAccountUser" }
      workflow_impersonation_roles  = { for identity, binding in google_service_account_iam_member.workflow_impersonation : identity => binding.role }
    }
    serverless = {
      api_image                     = google_cloud_run_v2_service.api.template[0].containers[0].image
      worker_image                  = google_cloud_run_v2_service.worker.template[0].containers[0].image
      api_ingress                   = google_cloud_run_v2_service.api.ingress
      worker_ingress                = google_cloud_run_v2_service.worker.ingress
      worker_invoker_count          = length([google_cloud_run_v2_service_iam_member.worker_task_invoker])
      worker_invoker_roles          = [google_cloud_run_v2_service_iam_member.worker_task_invoker.role]
      worker_invoker_members        = [google_cloud_run_v2_service_iam_member.worker_task_invoker.member]
      queue_enqueuer_count          = length([google_cloud_tasks_queue_iam_member.api_enqueuer])
      queue_enqueuer_roles          = [google_cloud_tasks_queue_iam_member.api_enqueuer.role]
      bucket_count                  = length(google_storage_bucket.private)
      public_prevention_count       = length([for bucket in values(google_storage_bucket.private) : bucket if bucket.public_access_prevention == "enforced"])
      uniform_access_count          = length([for bucket in values(google_storage_bucket.private) : bucket if bucket.uniform_bucket_level_access])
      versioned_bucket_count        = length([for bucket in values(google_storage_bucket.private) : bucket if bucket.versioning[0].enabled])
      release_reader_count          = length([google_storage_bucket_iam_member.release_api_read])
      release_reader_roles          = [google_storage_bucket_iam_member.release_api_read.role]
      release_reader_members        = [google_storage_bucket_iam_member.release_api_read.member]
      release_reader_is_api         = google_storage_bucket_iam_member.release_api_read.member == google_service_account.identities["api"].member
      release_worker_binding_count  = length([for binding in [google_storage_bucket_iam_member.release_api_read] : binding if binding.member == google_service_account.identities["worker"].member])
      bootstrap_reader_count        = length([google_storage_bucket_iam_member.bootstrap_request_read])
      bootstrap_reader_roles        = [google_storage_bucket_iam_member.bootstrap_request_read.role]
      bootstrap_prefixes            = [google_storage_bucket_iam_member.bootstrap_request_read.condition[0].expression]
      bootstrap_reader_is_bootstrap = google_storage_bucket_iam_member.bootstrap_request_read.member == google_service_account.identities["bootstrap"].member
      api_grant_key_count           = length([for env in google_cloud_run_v2_service.api.template[0].containers[0].env : env if env.name == "CLIENT_UPDATE_GRANT_KEY"])
      worker_grant_key_count        = length([for env in google_cloud_run_v2_service.worker.template[0].containers[0].env : env if env.name == "CLIENT_UPDATE_GRANT_KEY"])
      api_release_bucket_count      = length([for env in google_cloud_run_v2_service.api.template[0].containers[0].env : env if env.name == "ACCESS_RELEASE_BUCKET"])
      worker_release_bucket_count   = length([for env in google_cloud_run_v2_service.worker.template[0].containers[0].env : env if env.name == "ACCESS_RELEASE_BUCKET"])
      cloud_armor_policy_name       = google_compute_backend_service.api.security_policy
      http_redirect_count           = length([google_compute_global_forwarding_rule.http])
    }
    bootstrap_environment     = var.wif_trust["admin-bootstrap"].github_environment
    workflow_claim_categories = { for name, trust in var.wif_trust : name => sort(tolist(trust.workflow_claims)) }
  }
}
