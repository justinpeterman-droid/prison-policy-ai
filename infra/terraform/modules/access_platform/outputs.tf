output "logical_backup_service_account_email" { value = google_service_account.logical_backup.email }
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
      postgres_17       = google_sql_database_instance.postgres.database_version == "POSTGRES_17"
      production_ha     = google_sql_database_instance.postgres.settings[0].availability_type == "REGIONAL"
      deletion_boundary = google_sql_database_instance.postgres.deletion_protection == (var.environment == "production")
    }
    service_accounts = {
      count                     = length(google_service_account.identities) + 1
      distinct_account_id_count = length(toset(concat([for account in values(google_service_account.identities) : account.account_id], [google_service_account.logical_backup.account_id])))
      id_lengths                = concat([for account in values(google_service_account.identities) : length(account.account_id)], [length(google_service_account.logical_backup.account_id)])
    }
    wif = {
      provider_count                  = length(google_iam_workload_identity_pool_provider.workflow)
      distinct_provider_id_count      = length(toset([for provider in values(google_iam_workload_identity_pool_provider.workflow) : provider.workload_identity_pool_provider_id]))
      provider_id_lengths             = [for provider in values(google_iam_workload_identity_pool_provider.workflow) : length(provider.workload_identity_pool_provider_id)]
      pool_id_length                  = length(google_iam_workload_identity_pool.workflow.workload_identity_pool_id)
      impersonation_binding_count     = length(google_service_account_iam_member.workflow_impersonation)
      provider_specific_binding_count = length(google_service_account_iam_member.workflow_impersonation)
      workflow_identity_mapping_count = length([for name, provider in google_iam_workload_identity_pool_provider.workflow : provider if provider.attribute_mapping["attribute.workflow_identity"] == format("%q", name)])
      direct_claim_condition_count    = length([for provider in values(google_iam_workload_identity_pool_provider.workflow) : provider if strcontains(provider.attribute_condition, "assertion.workflow_ref") || strcontains(provider.attribute_condition, "assertion.job_workflow_ref")])
      principal_set_relations = {
        for identity, binding in google_service_account_iam_member.workflow_impersonation : identity => binding.member == "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.workflow.name}/attribute.workflow_identity/${identity}"
      }
    }
    secrets = {
      container_count = length(google_secret_manager_secret.containers)
      version_count   = length(google_secret_manager_secret_version.managed)
      binding_count   = length(google_secret_manager_secret_iam_member.least_privilege)
      binding_roles   = sort([for binding in values(google_secret_manager_secret_iam_member.least_privilege) : binding.role])
      exact_relations = {
        for key, binding in google_secret_manager_secret_iam_member.least_privilege : key => binding.role == (key == "bootstrap-initial-pin-adder" ? "roles/secretmanager.secretVersionAdder" : "roles/secretmanager.secretAccessor") && binding.member == google_service_account.identities[lookup({ api-database = "api", api-identity-pepper = "api", api-cursor-key = "api", api-client-update-grant-key = "api", api-legacy-access = "api", api-legacy-admin = "api", api-feedback = "api", api-session = "api", worker-database = "worker", migration-database = "migration", bootstrap-database = "bootstrap", bootstrap-initial-pin-adder = "bootstrap" }, key)].member && binding.secret_id == google_secret_manager_secret.containers[lookup({ api-database = "access-database-url", api-identity-pepper = "identity-hash-pepper", api-cursor-key = "cursor-signing-key", api-client-update-grant-key = "client-update-grant-key", api-legacy-access = "legacy-access-code", api-legacy-admin = "legacy-admin-code", api-feedback = "github-feedback-token", api-session = "flask-session-secret", worker-database = "access-database-url", migration-database = "access-database-url", bootstrap-database = "access-database-url", bootstrap-initial-pin-adder = "initial-admin-pin" }, key)].id
      }
    }
    iam = {
      project_binding_count = length(google_project_iam_member.least_privilege) + 1
      project_roles         = sort(concat([for key, binding in google_project_iam_member.least_privilege : key == "terraform-apply-secret-container-admin" ? "custom:secret-container-admin" : binding.role], ["custom:op04-infrastructure"]))
      exact_relations = {
        for key, binding in google_project_iam_member.least_privilege : key => binding.member == google_service_account.identities[local.project_iam_bindings[key].account].member && binding.role == local.project_iam_bindings[key].role
      }
      metric_writer_binding_count = length([
        for binding in values(google_project_iam_member.least_privilege) : binding
        if binding.role == "roles/monitoring.metricWriter"
      ])
      metric_writer_relations = {
        for key, binding in google_project_iam_member.least_privilege : key => binding.member == google_service_account.identities["worker"].member && key == "worker-metric-writer"
        if binding.role == "roles/monitoring.metricWriter"
      }
      op04_infrastructure_relation = google_project_iam_member.terraform_apply_op04_infrastructure.role == google_project_iam_custom_role.terraform_apply_op04_infrastructure.name && google_project_iam_member.terraform_apply_op04_infrastructure.member == google_service_account.identities["terraform_apply"].member
      custom_role = {
        id_category = google_project_iam_custom_role.terraform_apply_secret_containers.role_id == "accessSecretContainerAdmin"
        secret_payload_permission_count = length([
          for permission in google_project_iam_custom_role.terraform_apply_secret_containers.permissions : permission
          if permission == "secretmanager.versions.access" || permission == "secretmanager.versions.get"
        ])
      }
      op04_infrastructure_role = {
        id_category = google_project_iam_custom_role.terraform_apply_op04_infrastructure.role_id == "accessOp04Infrastructure"
        iam_role_lifecycle_count = length([
          for permission in google_project_iam_custom_role.terraform_apply_op04_infrastructure.permissions : permission
          if startswith(permission, "iam.roles.")
        ])
        forbidden_data_plane_permission_count = length([
          for permission in google_project_iam_custom_role.terraform_apply_op04_infrastructure.permissions : permission
          if startswith(permission, "storage.objects.") || startswith(permission, "cloudtasks.tasks.") || permission == "artifactregistry.repositories.uploadArtifacts" || startswith(permission, "run.jobs.") || permission == "run.services.updateTraffic" || startswith(permission, "secretmanager.")
        ])
      }
      state_binding_count           = length(google_storage_bucket_iam_member.terraform_state)
      state_roles                   = sort([for binding in values(google_storage_bucket_iam_member.terraform_state) : binding.role])
      exact_state_relations         = { for key, binding in google_storage_bucket_iam_member.terraform_state : key => binding.member == google_service_account.identities[key == "terraform-plan" ? "terraform_plan" : "terraform_apply"].member && binding.role == (key == "terraform-plan" ? "roles/storage.objectViewer" : "roles/storage.objectAdmin") }
      service_account_binding_count = length(concat(values(google_service_account_iam_member.deploy_runtime_user), values(google_service_account_iam_member.workflow_impersonation)))
      service_account_roles         = sort(concat([for binding in values(google_service_account_iam_member.deploy_runtime_user) : binding.role], [for binding in values(google_service_account_iam_member.workflow_impersonation) : binding.role]))
      deploy_runtime_relation_count = length([for binding in values(google_service_account_iam_member.deploy_runtime_user) : binding if binding.role == "roles/iam.serviceAccountUser"])
      exact_deploy_relations        = { for key, binding in google_service_account_iam_member.deploy_runtime_user : key => binding.member == google_service_account.identities["deploy"].member && binding.role == "roles/iam.serviceAccountUser" }
    }
    serverless = {
      same_digest                  = google_cloud_run_v2_service.api.template[0].containers[0].image == google_cloud_run_v2_service.worker.template[0].containers[0].image
      api_internal_lb_ingress      = google_cloud_run_v2_service.api.ingress == "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
      worker_internal_ingress      = google_cloud_run_v2_service.worker.ingress == "INGRESS_TRAFFIC_INTERNAL_ONLY"
      service_label_relations      = { api = alltrue([for value in values(google_cloud_run_v2_service.api.labels) : can(regex("^[a-z0-9_-]{0,63}$", value))]), worker = alltrue([for value in values(google_cloud_run_v2_service.worker.labels) : can(regex("^[a-z0-9_-]{0,63}$", value))]) }
      health_probe_relations       = { api = length(google_cloud_run_v2_service.api.template[0].containers[0].startup_probe) == 1 && length(google_cloud_run_v2_service.api.template[0].containers[0].liveness_probe) == 1 && google_cloud_run_v2_service.api.template[0].containers[0].startup_probe[0].http_get[0].path == "/health" && google_cloud_run_v2_service.api.template[0].containers[0].liveness_probe[0].http_get[0].path == "/health" && google_cloud_run_v2_service.api.template[0].containers[0].startup_probe[0].timeout_seconds == 5 && google_cloud_run_v2_service.api.template[0].containers[0].startup_probe[0].period_seconds == 10 && google_cloud_run_v2_service.api.template[0].containers[0].startup_probe[0].failure_threshold == 18 && google_cloud_run_v2_service.api.template[0].containers[0].liveness_probe[0].timeout_seconds == 5 && google_cloud_run_v2_service.api.template[0].containers[0].liveness_probe[0].period_seconds == 10 && google_cloud_run_v2_service.api.template[0].containers[0].liveness_probe[0].failure_threshold == 18, worker = length(google_cloud_run_v2_service.worker.template[0].containers[0].startup_probe) == 1 && length(google_cloud_run_v2_service.worker.template[0].containers[0].liveness_probe) == 1 && google_cloud_run_v2_service.worker.template[0].containers[0].startup_probe[0].tcp_socket[0].port == 8080 && google_cloud_run_v2_service.worker.template[0].containers[0].liveness_probe[0].tcp_socket[0].port == 8080 && google_cloud_run_v2_service.worker.template[0].containers[0].startup_probe[0].timeout_seconds == 5 && google_cloud_run_v2_service.worker.template[0].containers[0].startup_probe[0].period_seconds == 10 && google_cloud_run_v2_service.worker.template[0].containers[0].startup_probe[0].failure_threshold == 18 && google_cloud_run_v2_service.worker.template[0].containers[0].liveness_probe[0].timeout_seconds == 5 && google_cloud_run_v2_service.worker.template[0].containers[0].liveness_probe[0].period_seconds == 10 && google_cloud_run_v2_service.worker.template[0].containers[0].liveness_probe[0].failure_threshold == 18 }
      api_public_invoker_count     = length([for binding in concat([google_cloud_run_v2_service_iam_member.api_public_invoker, google_cloud_run_v2_service_iam_member.worker_task_invoker], values(google_cloud_run_v2_service_iam_member.deploy_services), values(google_cloud_run_v2_service_iam_member.rollback_services)) : binding if binding.name == google_cloud_run_v2_service.api.name && binding.role == "roles/run.invoker" && binding.member == "allUsers"])
      non_api_public_invoker_count = length([for binding in concat([google_cloud_run_v2_service_iam_member.api_public_invoker, google_cloud_run_v2_service_iam_member.worker_task_invoker], values(google_cloud_run_v2_service_iam_member.deploy_services), values(google_cloud_run_v2_service_iam_member.rollback_services)) : binding if binding.member == "allUsers" && binding.name != google_cloud_run_v2_service.api.name])
      worker_task_invoker_count    = length([for binding in concat([google_cloud_run_v2_service_iam_member.api_public_invoker, google_cloud_run_v2_service_iam_member.worker_task_invoker], values(google_cloud_run_v2_service_iam_member.deploy_services), values(google_cloud_run_v2_service_iam_member.rollback_services)) : binding if binding.name == google_cloud_run_v2_service.worker.name && binding.role == "roles/run.invoker" && binding.member == "serviceAccount:${google_service_account.identities["task_invoker"].email}"])
      queue_enqueuer_count         = length([for binding in [google_cloud_tasks_queue_iam_member.api_enqueuer] : binding if binding.role == "roles/cloudtasks.enqueuer" && binding.member == google_service_account.identities["api"].member])
      bucket_count                 = length(google_storage_bucket.private)
      public_prevention_count      = length([for bucket in values(google_storage_bucket.private) : bucket if bucket.public_access_prevention == "enforced"])
      uniform_access_count         = length([for bucket in values(google_storage_bucket.private) : bucket if bucket.uniform_bucket_level_access])
      versioned_bucket_count       = length([for bucket in values(google_storage_bucket.private) : bucket if bucket.versioning[0].enabled])
      logical_backup_retention     = try(tostring(google_storage_bucket.private["logical_backup"].retention_policy[0].retention_period) == "2592000", false)
      release_api_viewer_count     = length([for binding in concat([google_storage_bucket_iam_member.release_api_read, google_storage_bucket_iam_member.bootstrap_request_read, google_storage_bucket_iam_member.roster_migration_read, google_storage_bucket_iam_member.review_api_read], google_storage_bucket_iam_member.release_access_release_write) : binding if binding.bucket == google_storage_bucket.private["release"].name && binding.role == "roles/storage.objectViewer" && binding.member == google_service_account.identities["api"].member])
      release_other_viewer_count   = length([for binding in concat([google_storage_bucket_iam_member.release_api_read, google_storage_bucket_iam_member.bootstrap_request_read, google_storage_bucket_iam_member.roster_migration_read, google_storage_bucket_iam_member.review_api_read], google_storage_bucket_iam_member.release_access_release_write) : binding if binding.bucket == google_storage_bucket.private["release"].name && binding.role == "roles/storage.objectViewer" && binding.member != google_service_account.identities["api"].member])
      bootstrap_prefix_exact       = google_storage_bucket_iam_member.bootstrap_request_read.role == "roles/storage.objectViewer" && google_storage_bucket_iam_member.bootstrap_request_read.member == google_service_account.identities["bootstrap"].member && google_storage_bucket_iam_member.bootstrap_request_read.condition[0].expression == "resource.name.startsWith(\"projects/_/buckets/${google_storage_bucket.private["configuration"].name}/objects/admin-bootstrap-requests/\")"
      api_only_update_grant        = length([for env in google_cloud_run_v2_service.api.template[0].containers[0].env : env if env.name == "CLIENT_UPDATE_GRANT_KEY" && env.value_source[0].secret_key_ref[0].secret == google_secret_manager_secret.containers["client-update-grant-key"].secret_id]) == 1 && length([for env in google_cloud_run_v2_service.worker.template[0].containers[0].env : env if env.name == "CLIENT_UPDATE_GRANT_KEY"]) == 0
      api_only_release_bucket      = length([for env in google_cloud_run_v2_service.api.template[0].containers[0].env : env if env.name == "ACCESS_RELEASE_BUCKET" && env.value == google_storage_bucket.private["release"].name]) == 1 && length([for env in google_cloud_run_v2_service.worker.template[0].containers[0].env : env if env.name == "ACCESS_RELEASE_BUCKET"]) == 0
      api_secret_source_relations  = { for category, secret in { database = "access-database-url", pepper = "identity-hash-pepper", cursor = "cursor-signing-key", update_grant = "client-update-grant-key", legacy_access = "legacy-access-code", legacy_admin = "legacy-admin-code", feedback = "github-feedback-token" } : category => length([for env in google_cloud_run_v2_service.api.template[0].containers[0].env : env if try(env.value_source[0].secret_key_ref[0].secret == google_secret_manager_secret.containers[secret].secret_id, false)]) == 1 }
      worker_database_only         = length([for env in google_cloud_run_v2_service.worker.template[0].containers[0].env : env if try(env.value_source[0].secret_key_ref[0].secret == google_secret_manager_secret.containers["access-database-url"].secret_id, false)]) == 1 && length([for env in google_cloud_run_v2_service.worker.template[0].containers[0].env : env if length(env.value_source) > 0]) == 1
      cloud_armor_attached         = google_compute_backend_service.api.security_policy == google_compute_security_policy.edge.id
      http_redirect_count          = length([google_compute_global_forwarding_rule.http])
      deploy_scoped_relations      = { artifact = google_artifact_registry_repository_iam_member.deploy_writer.repository == google_artifact_registry_repository.backend.name && google_artifact_registry_repository_iam_member.deploy_writer.role == "roles/artifactregistry.writer", services = length(google_cloud_run_v2_service_iam_member.deploy_services) == 2 && alltrue([for binding in values(google_cloud_run_v2_service_iam_member.deploy_services) : binding.role == google_project_iam_custom_role.deploy_revision.name && binding.member == google_service_account.identities["deploy"].member]) }
      rollback_scoped_relations    = { services = length(google_cloud_run_v2_service_iam_member.rollback_services) == 2 && alltrue([for binding in values(google_cloud_run_v2_service_iam_member.rollback_services) : binding.role == google_project_iam_custom_role.rollback_traffic.name && binding.member == google_service_account.identities["rollback"].member]), permissions = toset(google_project_iam_custom_role.rollback_traffic.permissions) == toset(["run.services.get", "run.services.update", "run.operations.get", "run.revisions.get", "run.revisions.list"]) }
      access_release_scoped        = length(google_storage_bucket_iam_member.release_access_release_write) == (var.enable_access_release_identity ? 1 : 0) && alltrue([for binding in google_storage_bucket_iam_member.release_access_release_write : binding.role == "roles/storage.objectCreator" && binding.member == google_service_account.identities["access_release"].member && binding.condition[0].expression == "resource.name.startsWith(\"projects/_/buckets/${google_storage_bucket.private["release"].name}/objects/releases/\")"])
    }
    observability = {
      dashboard_count           = length(google_monitoring_dashboard.access)
      alert_policy_count        = 10 + length(google_monitoring_alert_policy.required)
      logical_export_schedule   = google_cloud_scheduler_job.logical_export_nightly.schedule
      logical_backup_is_creator = google_storage_bucket_iam_member.logical_backup_creator.role == "roles/storage.objectCreator"
      budget_thresholds         = sort(concat([for threshold in google_billing_budget.access.threshold_rules : threshold.threshold_percent], [for threshold in google_billing_budget.access.all_updates_rule : 1.0]))
    }
    bootstrap_environment     = var.wif_trust["admin-bootstrap"].github_environment
    workflow_claim_categories = { for name, trust in var.wif_trust : name => sort(tolist(trust.workflow_claims)) }
  }
}
