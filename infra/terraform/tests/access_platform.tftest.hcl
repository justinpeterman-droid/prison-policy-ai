mock_provider "google" {}

override_resource {
  target = module.access_platform.google_iam_workload_identity_pool.workflow
  values = {
    name = "projects/123456789/locations/global/workloadIdentityPools/access-test-wif"
  }
  override_during = plan
}

override_resource {
  target          = module.access_platform.google_service_account.identities["api"]
  values          = { member = "serviceAccount:fixture-api", name = "projects/slut-access-production-fixture/serviceAccounts/fixture-api@slut-access-production-fixture.iam.gserviceaccount.com" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_service_account.identities["worker"]
  values          = { member = "serviceAccount:fixture-worker", name = "projects/slut-access-production-fixture/serviceAccounts/fixture-worker@slut-access-production-fixture.iam.gserviceaccount.com" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_service_account.identities["task_invoker"]
  values          = { member = "serviceAccount:fixture-task-invoker", name = "projects/slut-access-production-fixture/serviceAccounts/fixture-task-invoker@slut-access-production-fixture.iam.gserviceaccount.com" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_service_account.identities["migration"]
  values          = { member = "serviceAccount:fixture-migration", name = "projects/slut-access-production-fixture/serviceAccounts/fixture-migration@slut-access-production-fixture.iam.gserviceaccount.com" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_service_account.identities["bootstrap"]
  values          = { member = "serviceAccount:fixture-bootstrap", name = "projects/slut-access-production-fixture/serviceAccounts/fixture-bootstrap@slut-access-production-fixture.iam.gserviceaccount.com" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_service_account.identities["terraform_plan"]
  values          = { member = "serviceAccount:fixture-terraform-plan", name = "projects/slut-access-production-fixture/serviceAccounts/fixture-terraform-plan@slut-access-production-fixture.iam.gserviceaccount.com" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_service_account.identities["terraform_apply"]
  values          = { member = "serviceAccount:fixture-terraform-apply", name = "projects/slut-access-production-fixture/serviceAccounts/fixture-terraform-apply@slut-access-production-fixture.iam.gserviceaccount.com" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_service_account.identities["deploy"]
  values          = { member = "serviceAccount:fixture-deploy", name = "projects/slut-access-production-fixture/serviceAccounts/fixture-deploy@slut-access-production-fixture.iam.gserviceaccount.com" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_service_account.identities["rollback"]
  values          = { member = "serviceAccount:fixture-rollback", name = "projects/slut-access-production-fixture/serviceAccounts/fixture-rollback@slut-access-production-fixture.iam.gserviceaccount.com" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_service_account.identities["admin_bootstrap"]
  values          = { member = "serviceAccount:fixture-admin-bootstrap", name = "projects/slut-access-production-fixture/serviceAccounts/fixture-admin-bootstrap@slut-access-production-fixture.iam.gserviceaccount.com" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_secret_manager_secret.containers["access-database-url"]
  values          = { id = "fixture-secret-access-database-url" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_secret_manager_secret.containers["identity-hash-pepper"]
  values          = { id = "fixture-secret-identity-hash-pepper" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_secret_manager_secret.containers["cursor-signing-key"]
  values          = { id = "fixture-secret-cursor-signing-key" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_secret_manager_secret.containers["client-update-grant-key"]
  values          = { id = "fixture-secret-client-update-grant-key" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_secret_manager_secret.containers["legacy-access-code"]
  values          = { id = "fixture-secret-legacy-access-code" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_secret_manager_secret.containers["legacy-admin-code"]
  values          = { id = "fixture-secret-legacy-admin-code" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_secret_manager_secret.containers["github-feedback-token"]
  values          = { id = "fixture-secret-github-feedback-token" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_secret_manager_secret.containers["flask-session-secret"]
  values          = { id = "fixture-secret-flask-session-secret" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_secret_manager_secret.containers["initial-admin-pin"]
  values          = { id = "initial-admin-pin" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_project_iam_custom_role.terraform_apply_secret_containers
  values          = { name = "projects/slut-access-production-fixture/roles/accessSecretContainerAdmin" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_project_iam_custom_role.terraform_plan_readonly
  values          = { name = "projects/slut-access-production-fixture/roles/accessTerraformPlanRead" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_project_iam_custom_role.terraform_apply_service_accounts
  values          = { name = "projects/slut-access-production-fixture/roles/accessServiceAccountLifecycle" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_project_iam_custom_role.terraform_apply_op04_infrastructure
  values          = { name = "projects/slut-access-production-fixture/roles/accessOp04Infrastructure" }
  override_during = plan
}

run "private_platform_contract" {
  command = plan

  variables {
    project_id                        = "slut-access-production-fixture"
    source_repository                 = "justinpeterman-droid/prison-policy-ai"
    state_bucket_name                 = "slut-access-production-fixture"
    storage_log_bucket_name           = "access-test-fixture-audit-logs"
    artifact_registry_kms_key_name    = "projects/fixture-project/locations/us-central1/keyRings/fixture-key-ring/cryptoKeys/fixture-artifact-key"
    labels                            = { fixture = "op03" }
    image_digest                      = "example.invalid/access/fixture@sha256:0000000000000000000000000000000000000000000000000000000000000000"
    source_commit                     = "1111111111111111111111111111111111111111"
    release_version                   = "development"
    api_version                       = "v1"
    latest_client_version             = "development"
    minimum_client_version            = "development"
    minimum_server_version            = "development"
    release_notes                     = "Fixture release."
    managed_hostname                  = "fixture.example.invalid"
    dns_zone_name                     = "fixture-zone"
    image_repository_id               = "fixture-images"
    queue_max_attempts                = 5
    gcp_model_location                = "us-central1"
    agent_builder_location            = "global"
    agent_builder_collection          = "fixture-collection"
    agent_builder_engine_id           = "fixture-engine"
    agent_builder_serving_config      = "fixture-serving"
    fast_model                        = "fixture-fast"
    pro_model                         = "fixture-pro"
    legacy_report_mode                = "disabled"
    review_object_prefix              = "review-lab/"
    log_level                         = "INFO"
    api_min_instances                 = 1
    api_max_instances                 = 10
    api_max_concurrency               = 20
    worker_min_instances              = 0
    worker_max_instances              = 10
    worker_max_concurrency            = 4
    notification_channel_ids          = []
    billing_account_id                = "fixture-billing-account"
    monthly_budget_amount             = 1
    budget_pubsub_topic               = "projects/slut-access-production-fixture/topics/access-budget-alerts"
    observability_owner_role          = "platform-operations"
    sensitive_log_scanner_metric_type = "custom.googleapis.com/access_sensitive_log_scanner_failure"
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.database.postgres_18
    error_message = "Cloud SQL must be PostgreSQL 18."
  }

  assert {
    condition = module.access_platform.database_name == "access_production" ? (
      module.access_platform.terraform_test_contract.database.production_ha && module.access_platform.terraform_test_contract.database.deletion_boundary
      ) : (
      !module.access_platform.terraform_test_contract.database.production_ha && module.access_platform.terraform_test_contract.database.deletion_boundary
    )
    error_message = "Production must be regional and deletion-protected; test must remain zonal and removable."
  }

  assert {
    condition = module.access_platform.terraform_test_contract.service_accounts.count == (
      module.access_platform.database_name == "access_production" ? 11 : 10
    ) + 1 && module.access_platform.terraform_test_contract.service_accounts.distinct_account_id_count == module.access_platform.terraform_test_contract.service_accounts.count && alltrue([for id_length in module.access_platform.terraform_test_contract.service_accounts.id_lengths : id_length <= 30])
    error_message = "Test and production must include the dedicated provider-valid logical-backup identity."
  }

  assert {
    condition = module.access_platform.terraform_test_contract.wif.provider_count == (
      module.access_platform.database_name == "access_production" ? 6 : 5
    ) && module.access_platform.terraform_test_contract.wif.distinct_provider_id_count == module.access_platform.terraform_test_contract.wif.provider_count && module.access_platform.terraform_test_contract.wif.impersonation_binding_count == module.access_platform.terraform_test_contract.wif.provider_count && module.access_platform.terraform_test_contract.wif.provider_specific_binding_count == module.access_platform.terraform_test_contract.wif.provider_count && alltrue(values(module.access_platform.terraform_test_contract.wif.principal_set_relations)) && module.access_platform.terraform_test_contract.wif.pool_id_length <= 32 && alltrue([for id_length in module.access_platform.terraform_test_contract.wif.provider_id_lengths : id_length <= 32]) && module.access_platform.terraform_test_contract.wif.direct_claim_condition_count == module.access_platform.terraform_test_contract.wif.provider_count
    error_message = "Test and production must expose distinct provider-valid WIF identities with one provider-specific binding each."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.observability.pitr_enabled && module.access_platform.terraform_test_contract.observability.backup_bucket_private && module.access_platform.terraform_test_contract.observability.backup_export_permissions == toset(["cloudsql.instances.export", "cloudsql.instances.get"]) && module.access_platform.terraform_test_contract.observability.backup_instance_condition && module.access_platform.terraform_test_contract.observability.scheduler_workflow_condition && !module.access_platform.terraform_test_contract.observability.logical_export_scheduler_enabled && module.access_platform.terraform_test_contract.observability.logical_export_schedule == null
    error_message = "OP-05 backup identity must be export-only on the exact instance and invoke only the exact workflow."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.observability.dashboard_count == 4
    error_message = "OP-05 must retain exactly four dashboards."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.observability.alert_policy_count == 17
    error_message = "OP-05 must retain all always-on alerts, including distinct failed-job latency, while the export workflow is externally gated."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.observability.logical_backup_is_creator
    error_message = "OP-05 must retain its creator-only logical backup bucket permission while scheduling is externally gated."
  }

  assert {
    condition     = toset(module.access_platform.terraform_test_contract.observability.budget_thresholds) == toset(["0.5", "0.8", "0.9", "1", "1.2"])
    error_message = "OP-05 must retain its exact budget thresholds."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.secrets.container_count == 9
    error_message = "Only the nine approved empty secret containers may exist."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.secrets.version_count == 0 && module.access_platform.terraform_test_contract.secrets.binding_count == 12 && length([for role in module.access_platform.terraform_test_contract.secrets.binding_roles : role if role == "roles/secretmanager.secretAccessor"]) == 11 && length([for role in module.access_platform.terraform_test_contract.secrets.binding_roles : role if role == "roles/secretmanager.secretVersionAdder"]) == 1 && alltrue(values(module.access_platform.terraform_test_contract.secrets.exact_relations))
    error_message = "Update-grant, bootstrap PIN, and workflow secret-access boundaries must remain least privilege."
  }

  assert {
    condition = module.access_platform.terraform_test_contract.iam.project_binding_count == 17 && length(module.access_platform.terraform_test_contract.iam.project_roles) == 17 && length(setsubtract(toset(module.access_platform.terraform_test_contract.iam.project_roles), toset([
      "roles/cloudsql.client", "roles/cloudtasks.enqueuer", "roles/monitoring.metricWriter", "roles/iam.securityReviewer", "roles/secretmanager.viewer", "roles/compute.networkAdmin", "roles/servicenetworking.networksAdmin", "roles/cloudsql.admin", "roles/iam.workloadIdentityPoolAdmin", "roles/resourcemanager.projectIamAdmin", "custom:terraform-plan-readonly", "custom:service-account-lifecycle", "custom:secret-container-admin", "custom:op04-infrastructure",
      ]))) == 0 && length(setsubtract(toset([
      "roles/cloudsql.client", "roles/cloudtasks.enqueuer", "roles/monitoring.metricWriter", "roles/iam.securityReviewer", "roles/secretmanager.viewer", "roles/compute.networkAdmin", "roles/servicenetworking.networksAdmin", "roles/cloudsql.admin", "roles/iam.workloadIdentityPoolAdmin", "roles/resourcemanager.projectIamAdmin", "custom:terraform-plan-readonly", "custom:service-account-lifecycle", "custom:secret-container-admin", "custom:op04-infrastructure",
    ]), toset(module.access_platform.terraform_test_contract.iam.project_roles))) == 0 && length([for role in module.access_platform.terraform_test_contract.iam.project_roles : role if role == "roles/cloudsql.client"]) == 4 && module.access_platform.terraform_test_contract.iam.metric_writer_binding_count == 1 && alltrue(values(module.access_platform.terraform_test_contract.iam.metric_writer_relations)) && alltrue(values(module.access_platform.terraform_test_contract.iam.exact_relations)) && module.access_platform.terraform_test_contract.iam.op04_infrastructure_relation && module.access_platform.terraform_test_contract.iam.custom_role.id_category && module.access_platform.terraform_test_contract.iam.custom_role.secret_payload_permission_count == 0 && module.access_platform.terraform_test_contract.iam.op04_infrastructure_role.id_category && module.access_platform.terraform_test_contract.iam.op04_infrastructure_role.iam_role_lifecycle_count == 4 && module.access_platform.terraform_test_contract.iam.op04_infrastructure_role.forbidden_data_plane_permission_count == 0 && module.access_platform.terraform_test_contract.iam.terraform_plan_role.id_category && module.access_platform.terraform_test_contract.iam.terraform_plan_role.binding_exact && module.access_platform.terraform_test_contract.iam.service_account_lifecycle_role.id_category && module.access_platform.terraform_test_contract.iam.service_account_lifecycle_role.binding_exact && module.access_platform.terraform_test_contract.iam.service_account_lifecycle_role.credential_permission_count == 0
    error_message = "The complete project IAM collection must retain only the reviewed management and runtime roles."
  }

  assert {
    condition = module.access_platform.terraform_test_contract.iam.terraform_plan_role.permissions == toset([
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
      "serviceusage.services.get", "serviceusage.services.list",
      "servicenetworking.services.get",
      "storage.buckets.get", "storage.buckets.getIamPolicy", "storage.buckets.list",
      "workflows.workflows.get", "workflows.workflows.list",
    ])
    error_message = "Terraform plan must receive only the read permissions derived from managed resource types."
  }

  assert {
    condition = module.access_platform.terraform_test_contract.iam.service_account_lifecycle_role.permissions == toset([
      "iam.serviceAccounts.create", "iam.serviceAccounts.delete", "iam.serviceAccounts.get", "iam.serviceAccounts.getIamPolicy", "iam.serviceAccounts.list", "iam.serviceAccounts.setIamPolicy", "iam.serviceAccounts.update",
    ])
    error_message = "Terraform apply may manage service-account lifecycle and IAM only, never credentials or impersonation."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.iam.state_binding_count == 2 && toset(module.access_platform.terraform_test_contract.iam.state_roles) == toset(["roles/storage.objectViewer", "roles/storage.objectAdmin"]) && alltrue(values(module.access_platform.terraform_test_contract.iam.exact_state_relations)) && module.access_platform.terraform_test_contract.iam.service_account_binding_count == (module.access_platform.database_name == "access_production" ? 9 : 8) && length([for role in module.access_platform.terraform_test_contract.iam.service_account_roles : role if role == "roles/iam.serviceAccountUser"]) == 3 && length([for role in module.access_platform.terraform_test_contract.iam.service_account_roles : role if role == "roles/iam.workloadIdentityUser"]) == (module.access_platform.database_name == "access_production" ? 6 : 5) && module.access_platform.terraform_test_contract.iam.deploy_runtime_relation_count == 3 && alltrue(values(module.access_platform.terraform_test_contract.iam.exact_deploy_relations))
    error_message = "All state, deploy, and workflow service-account bindings must remain exact and distinct."
  }

  assert {
    condition     = module.access_platform.database_name == "access_test" ? module.access_platform.terraform_test_contract.bootstrap_environment == "test" : module.access_platform.terraform_test_contract.bootstrap_environment == "production-deploy"
    error_message = "Bootstrap trust must use test or production-deploy for its matching root."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.wif.workflow_identity_mapping_count == module.access_platform.terraform_test_contract.wif.provider_count
    error_message = "Every workflow account must have a separate provider-specific identity category."
  }

  assert {
    condition     = alltrue(values(module.access_platform.terraform_test_contract.wif.principal_set_relations)) && module.access_platform.terraform_test_contract.iam.deploy_runtime_relation_count == 3
    error_message = "Every reviewed workflow must have exactly its own provider and impersonation role; deploy may use only API, worker, and migration runtimes."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.wif.approved_repository_configured && module.access_platform.terraform_test_contract.wif.exact_subject_condition_count == module.access_platform.terraform_test_contract.wif.provider_count
    error_message = "Every GitHub WIF provider must constrain assertion.sub to its exact repository and approved environment identity."
  }

  assert {
    condition     = toset(module.access_platform.terraform_test_contract.workflow_claim_categories["terraform-plan"]) == toset(["job_workflow_ref", "workflow_ref"])
    error_message = "Terraform plan must permit both its top-level and reusable workflow claims."
  }

  assert {
    condition     = toset(module.access_platform.terraform_test_contract.workflow_claim_categories["terraform-apply"]) == toset(["job_workflow_ref"])
    error_message = "Terraform apply must permit its reusable workflow claim only."
  }

  assert {
    condition     = toset(module.access_platform.terraform_test_contract.workflow_claim_categories["deploy"]) == toset(["workflow_ref"]) && toset(module.access_platform.terraform_test_contract.workflow_claim_categories["rollback"]) == toset(["workflow_ref"]) && toset(module.access_platform.terraform_test_contract.workflow_claim_categories["admin-bootstrap"]) == toset(["workflow_ref"]) && toset(module.access_platform.terraform_test_contract.workflow_claim_categories["access-release"]) == toset(["workflow_ref"])
    error_message = "Deploy, rollback, bootstrap, and release must permit top-level workflow claims only."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.serverless.same_digest && module.access_platform.terraform_test_contract.serverless.api_internal_lb_ingress && module.access_platform.terraform_test_contract.serverless.worker_internal_ingress && alltrue(values(module.access_platform.terraform_test_contract.serverless.service_label_relations)) && alltrue(values(module.access_platform.terraform_test_contract.serverless.health_probe_relations))
    error_message = "API and worker must use one digest, bounded private health probes, exact ingress boundaries, and sanitized shared labels."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.network.enable_flow_logs && module.access_platform.terraform_test_contract.network.default_deny_ingress
    error_message = "The private subnet must emit flow logs and the custom VPC must have an explicit terminal deny-ingress firewall."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.serverless.cloud_armor_log4j_protection && module.access_platform.terraform_test_contract.serverless.artifact_registry_kms_exact
    error_message = "Cloud Armor must deny the Log4j canary before throttling and Artifact Registry must use the required external KMS key."
  }

  assert {
    condition = module.access_platform.terraform_test_contract.database.postgres_18 && module.access_platform.terraform_test_contract.database.ssl_mode == "TRUSTED_CLIENT_CERTIFICATE_REQUIRED" && module.access_platform.terraform_test_contract.database.flag_values == {
      "cloudsql.enable_pgaudit"    = "on"
      "log_checkpoints"            = "on"
      "log_connections"            = "on"
      "log_disconnections"         = "on"
      "log_duration"               = "on"
      "log_hostname"               = "on"
      "log_lock_waits"             = "on"
      "log_min_duration_statement" = "-1"
      "log_min_error_statement"    = "error"
      "log_min_messages"           = "warning"
      "log_statement"              = "ddl"
      "pgaudit.log"                = "ddl,role,write"
    }
    error_message = "Cloud SQL must use PostgreSQL 18, require trusted client certificates, and retain the exact audited logging flags."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.serverless.api_public_invoker_count == 1 && module.access_platform.terraform_test_contract.serverless.non_api_public_invoker_count == 0 && module.access_platform.terraform_test_contract.serverless.worker_task_invoker_count == 1 && module.access_platform.terraform_test_contract.serverless.queue_enqueuer_count == 1
    error_message = "Only API may expose public invocation; worker invocation and queue enqueue remain identity-scoped."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.serverless.bucket_count == 5 && module.access_platform.terraform_test_contract.serverless.public_prevention_count == 5 && module.access_platform.terraform_test_contract.serverless.uniform_access_count == 5 && module.access_platform.terraform_test_contract.serverless.versioned_bucket_count == 5 && module.access_platform.terraform_test_contract.serverless.logical_backup_retention
    error_message = "All five storage buckets must be private, uniform, and versioned."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.serverless.release_api_viewer_count == 1 && module.access_platform.terraform_test_contract.serverless.release_other_viewer_count == 0 && module.access_platform.terraform_test_contract.serverless.bootstrap_prefix_exact
    error_message = "Release access must be API read-only and bootstrap access must remain prefix-only read-only."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.serverless.api_only_update_grant && module.access_platform.terraform_test_contract.serverless.api_only_release_bucket && alltrue(values(module.access_platform.terraform_test_contract.serverless.api_secret_source_relations)) && module.access_platform.terraform_test_contract.serverless.worker_database_only && module.access_platform.terraform_test_contract.serverless.cloud_armor_attached && module.access_platform.terraform_test_contract.serverless.http_redirect_count == 1 && alltrue(values(module.access_platform.terraform_test_contract.serverless.deploy_scoped_relations)) && alltrue(values(module.access_platform.terraform_test_contract.serverless.rollback_scoped_relations)) && module.access_platform.terraform_test_contract.serverless.access_release_scoped
    error_message = "Only API may receive the update grant and release bucket; HTTP must redirect to HTTPS."
  }

  assert {
    condition = module.access_platform.terraform_test_contract.jobs.names == {
      migration     = "access-test-migrate"
      roster_import = "access-test-roster-import"
      bootstrap     = "access-test-bootstrap-admin"
    }
    error_message = "OP-06 must create the three exact environment-scoped job names."
  }

  assert {
    condition     = join("\u0000", module.access_platform.terraform_test_contract.jobs.commands.migration) == join("\u0000", ["python", "-m", "backend.jobs.migration", "upgrade"]) && join("\u0000", module.access_platform.terraform_test_contract.jobs.commands.roster_import) == join("\u0000", ["python", "-m", "backend.jobs.roster_import", "--source-uri", "gs://access-test-roster/operator-supplied-roster.json", "--corrections-uri", "gs://access-test-roster/operator-supplied-corrections.json", "--report-uri", "gs://access-test-roster/operator-supplied-report.json", "--expected-sha256", "0000000000000000000000000000000000000000000000000000000000000000"]) && join("\u0000", module.access_platform.terraform_test_contract.jobs.commands.bootstrap) == join("\u0000", ["python", "-m", "backend.jobs.admin_bootstrap", "--request-uri", "gs://access-test-configuration/admin-bootstrap-requests/00000000-0000-4000-8000-000000000001.json", "--expected-sha256", "0000000000000000000000000000000000000000000000000000000000000000"])
    error_message = "OP-06 jobs must expose only the reviewed deterministic commands and arguments."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.jobs.identities.migration == module.access_platform.migration_service_account_email && module.access_platform.terraform_test_contract.jobs.identities.roster_import == module.access_platform.migration_service_account_email && module.access_platform.terraform_test_contract.jobs.identities.bootstrap == module.access_platform.bootstrap_service_account_email && alltrue([for value in values(module.access_platform.terraform_test_contract.jobs.max_retries) : value == 0]) && module.access_platform.terraform_test_contract.jobs.image_digest_exact
    error_message = "Migration and roster jobs must use migration identity; bootstrap must use bootstrap identity; retries must be disabled."
  }

  assert {
    condition     = alltrue([for count in values(module.access_platform.terraform_test_contract.jobs.cloudsql_mounts) : count == 1])
    error_message = "Every OP-06 job must mount its Cloud SQL volume at /cloudsql."
  }

  assert {
    condition = module.access_platform.terraform_test_contract.jobs.bootstrap_environment == {
      ADMIN_BOOTSTRAP_REQUEST_BUCKET = "access-test-configuration"
      ADMIN_BOOTSTRAP_REQUEST_PREFIX = "admin-bootstrap-requests/"
      INITIAL_ADMIN_PIN_SECRET       = "initial-admin-pin"
    }
    error_message = "Bootstrap must receive only the exact bucket, prefix, and secret parent runtime configuration."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.jobs.bootstrap_invoker_exact && module.access_platform.terraform_test_contract.jobs.invoker_binding_count == 1 && module.access_platform.terraform_test_contract.jobs.public_invoker_count == 0 && module.access_platform.terraform_test_contract.jobs.scheduled_target_count == 0 && module.access_platform.terraform_test_contract.jobs.bootstrap_workflow_service_binding_count == 0
    error_message = "Only the admin-bootstrap workflow identity may invoke bootstrap; OP-06 jobs must be private and unscheduled."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.jobs.apply_job_relation && module.access_platform.terraform_test_contract.jobs.apply_runtime_relations && module.access_platform.terraform_test_contract.jobs.apply_job_permissions == toset(["run.jobs.create", "run.jobs.delete", "run.jobs.get", "run.jobs.getIamPolicy", "run.jobs.list", "run.jobs.setIamPolicy", "run.jobs.update", "run.operations.get"]) && !contains(module.access_platform.terraform_test_contract.jobs.apply_job_permissions, "run.jobs.run")
    error_message = "Terraform apply must provision and bind OP-06 jobs without permission to execute them."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.jobs.deploy_job_relations && module.access_platform.terraform_test_contract.jobs.deploy_job_permissions == toset(["run.jobs.get", "run.jobs.run", "run.jobs.runWithOverrides", "run.jobs.update", "run.operations.get"]) && module.access_platform.terraform_test_contract.jobs.bootstrap_deploy_count == 0
    error_message = "Deploy may update and invoke only migration and roster jobs; it must never receive bootstrap access."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.jobs.report_writer_exact
    error_message = "Migration runtime may create only the exact approved private roster report object."
  }
}
override_resource {
  target          = module.access_platform.google_service_account.identities["access_release"]
  values          = { member = "serviceAccount:fixture-access-release", name = "projects/fixture/serviceAccounts/fixture-access-release@fixture.iam.gserviceaccount.com" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_project_iam_custom_role.deploy_revision
  values          = { name = "projects/fixture/roles/accessDeployRevision" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_project_iam_custom_role.rollback_traffic
  values          = { name = "projects/fixture/roles/accessRollbackTraffic" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_artifact_registry_repository.backend
  values          = { name = "fixture-backend" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_compute_security_policy.edge
  values          = { id = "fixture-edge-policy" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_compute_backend_service.api
  values          = { security_policy = "fixture-edge-policy" }
  override_during = plan
}
