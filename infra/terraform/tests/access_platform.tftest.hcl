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
  values          = { id = "fixture-secret-initial-admin-pin" }
  override_during = plan
}
override_resource {
  target          = module.access_platform.google_project_iam_custom_role.terraform_apply_secret_containers
  values          = { name = "projects/slut-access-production-fixture/roles/accessSecretContainerAdmin" }
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
    project_id                   = "slut-access-production-fixture"
    source_repository            = "example.invalid/agency/prison-policy-ai"
    state_bucket_name            = "slut-access-production-fixture"
    labels                       = { fixture = "op03" }
    image_digest                 = "example.invalid/access/fixture@sha256:0000000000000000000000000000000000000000000000000000000000000000"
    source_commit                = "1111111111111111111111111111111111111111"
    release_version              = "development"
    api_version                  = "v1"
    latest_client_version        = "development"
    minimum_client_version       = "development"
    minimum_server_version       = "development"
    release_notes                = "Fixture release."
    managed_hostname             = "fixture.example.invalid"
    dns_zone_name                = "fixture-zone"
    image_repository_id          = "fixture-images"
    queue_max_attempts           = 5
    gcp_model_location           = "us-central1"
    agent_builder_location       = "global"
    agent_builder_collection     = "fixture-collection"
    agent_builder_engine_id      = "fixture-engine"
    agent_builder_serving_config = "fixture-serving"
    fast_model                   = "fixture-fast"
    pro_model                    = "fixture-pro"
    legacy_report_mode           = "disabled"
    review_object_prefix         = "review-lab/"
    log_level                    = "INFO"
    api_min_instances            = 1
    api_max_instances            = 10
    api_max_concurrency          = 20
    worker_min_instances         = 0
    worker_max_instances         = 10
    worker_max_concurrency       = 4
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.database.postgres_17
    error_message = "Cloud SQL must be PostgreSQL 17."
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
    ) && module.access_platform.terraform_test_contract.service_accounts.distinct_account_id_count == module.access_platform.terraform_test_contract.service_accounts.count && alltrue([for id_length in module.access_platform.terraform_test_contract.service_accounts.id_lengths : id_length <= 30])
    error_message = "Test and production must have exactly ten and eleven distinct provider-valid service accounts."
  }

  assert {
    condition = module.access_platform.terraform_test_contract.wif.provider_count == (
      module.access_platform.database_name == "access_production" ? 6 : 5
    ) && module.access_platform.terraform_test_contract.wif.distinct_provider_id_count == module.access_platform.terraform_test_contract.wif.provider_count && module.access_platform.terraform_test_contract.wif.impersonation_binding_count == module.access_platform.terraform_test_contract.wif.provider_count && module.access_platform.terraform_test_contract.wif.provider_specific_binding_count == module.access_platform.terraform_test_contract.wif.provider_count && alltrue(values(module.access_platform.terraform_test_contract.wif.principal_set_relations)) && module.access_platform.terraform_test_contract.wif.pool_id_length <= 32 && alltrue([for id_length in module.access_platform.terraform_test_contract.wif.provider_id_lengths : id_length <= 32]) && module.access_platform.terraform_test_contract.wif.direct_claim_condition_count == module.access_platform.terraform_test_contract.wif.provider_count
    error_message = "Test and production must expose distinct provider-valid WIF identities with one provider-specific binding each."
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
    condition = module.access_platform.terraform_test_contract.iam.project_binding_count == 16 && length(module.access_platform.terraform_test_contract.iam.project_roles) == 16 && length(setsubtract(toset(module.access_platform.terraform_test_contract.iam.project_roles), toset([
      "roles/cloudsql.client", "roles/cloudtasks.enqueuer", "roles/viewer", "roles/iam.securityReviewer", "roles/secretmanager.viewer", "roles/compute.networkAdmin", "roles/servicenetworking.networksAdmin", "roles/cloudsql.admin", "roles/iam.serviceAccountAdmin", "roles/iam.workloadIdentityPoolAdmin", "roles/resourcemanager.projectIamAdmin", "custom:secret-container-admin", "custom:op04-infrastructure",
      ]))) == 0 && length(setsubtract(toset([
      "roles/cloudsql.client", "roles/cloudtasks.enqueuer", "roles/viewer", "roles/iam.securityReviewer", "roles/secretmanager.viewer", "roles/compute.networkAdmin", "roles/servicenetworking.networksAdmin", "roles/cloudsql.admin", "roles/iam.serviceAccountAdmin", "roles/iam.workloadIdentityPoolAdmin", "roles/resourcemanager.projectIamAdmin", "custom:secret-container-admin", "custom:op04-infrastructure",
    ]), toset(module.access_platform.terraform_test_contract.iam.project_roles))) == 0 && length([for role in module.access_platform.terraform_test_contract.iam.project_roles : role if role == "roles/cloudsql.client"]) == 4 && alltrue(values(module.access_platform.terraform_test_contract.iam.exact_relations)) && module.access_platform.terraform_test_contract.iam.op04_infrastructure_relation && module.access_platform.terraform_test_contract.iam.custom_role.id_category && module.access_platform.terraform_test_contract.iam.custom_role.secret_payload_permission_count == 0 && module.access_platform.terraform_test_contract.iam.op04_infrastructure_role.id_category && module.access_platform.terraform_test_contract.iam.op04_infrastructure_role.iam_role_lifecycle_count == 4 && module.access_platform.terraform_test_contract.iam.op04_infrastructure_role.forbidden_data_plane_permission_count == 0
    error_message = "The complete project IAM collection must retain only the reviewed management and runtime roles."
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
