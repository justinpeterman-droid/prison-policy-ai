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

run "private_platform_contract" {
  command = plan

  variables {
    project_id        = "slut-access-production-fixture"
    source_repository = "example.invalid/agency/prison-policy-ai"
    state_bucket_name = "slut-access-production-fixture"
    labels            = { fixture = "op03" }
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.database.postgres_17
    error_message = "Cloud SQL must be PostgreSQL 17."
  }

  assert {
    condition = module.access_platform.database_name == "access_production" ? (
      module.access_platform.terraform_test_contract.database.availability_type == "REGIONAL" && module.access_platform.terraform_test_contract.database.deletion_protected
      ) : (
      module.access_platform.terraform_test_contract.database.availability_type == "ZONAL" && !module.access_platform.terraform_test_contract.database.deletion_protected
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
    condition = module.access_platform.terraform_test_contract.secrets.container_count == 9 && length(setsubtract(toset(module.access_platform.terraform_test_contract.secrets.names), toset([
      "access-database-url", "identity-hash-pepper", "cursor-signing-key",
      "client-update-grant-key", "legacy-access-code", "legacy-admin-code",
      "github-feedback-token", "flask-session-secret", "initial-admin-pin",
      ]))) == 0 && length(setsubtract(toset([
      "access-database-url", "identity-hash-pepper", "cursor-signing-key",
      "client-update-grant-key", "legacy-access-code", "legacy-admin-code",
      "github-feedback-token", "flask-session-secret", "initial-admin-pin",
    ]), toset(module.access_platform.terraform_test_contract.secrets.names))) == 0
    error_message = "Only the nine approved empty secret containers may exist."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.secrets.version_count == 0 && module.access_platform.terraform_test_contract.secrets.binding_count == 12 && toset(module.access_platform.terraform_test_contract.secrets.binding_keys) == toset(["api-database", "api-identity-pepper", "api-cursor-key", "api-client-update-grant-key", "api-legacy-access", "api-legacy-admin", "api-feedback", "api-session", "worker-database", "migration-database", "bootstrap-database", "bootstrap-initial-pin-adder"]) && length([for role in module.access_platform.terraform_test_contract.secrets.binding_roles : role if role == "roles/secretmanager.secretAccessor"]) == 11 && length([for role in module.access_platform.terraform_test_contract.secrets.binding_roles : role if role == "roles/secretmanager.secretVersionAdder"]) == 1 && alltrue(values(module.access_platform.terraform_test_contract.secrets.exact_relations))
    error_message = "Update-grant, bootstrap PIN, and workflow secret-access boundaries must remain least privilege."
  }

  assert {
    condition = module.access_platform.terraform_test_contract.iam.project_binding_count == 15 && length(module.access_platform.terraform_test_contract.iam.project_roles) == 15 && length(setsubtract(toset(module.access_platform.terraform_test_contract.iam.project_roles), toset([
      "roles/cloudsql.client", "roles/cloudtasks.enqueuer", "roles/viewer", "roles/iam.securityReviewer", "roles/secretmanager.viewer", "roles/compute.networkAdmin", "roles/servicenetworking.networksAdmin", "roles/cloudsql.admin", "roles/iam.serviceAccountAdmin", "roles/iam.workloadIdentityPoolAdmin", "roles/resourcemanager.projectIamAdmin", "projects/slut-access-production-fixture/roles/accessSecretContainerAdmin",
      ]))) == 0 && length(setsubtract(toset([
      "roles/cloudsql.client", "roles/cloudtasks.enqueuer", "roles/viewer", "roles/iam.securityReviewer", "roles/secretmanager.viewer", "roles/compute.networkAdmin", "roles/servicenetworking.networksAdmin", "roles/cloudsql.admin", "roles/iam.serviceAccountAdmin", "roles/iam.workloadIdentityPoolAdmin", "roles/resourcemanager.projectIamAdmin", "projects/slut-access-production-fixture/roles/accessSecretContainerAdmin",
    ]), toset(module.access_platform.terraform_test_contract.iam.project_roles))) == 0 && length([for role in module.access_platform.terraform_test_contract.iam.project_roles : role if role == "roles/cloudsql.client"]) == 4 && alltrue(values(module.access_platform.terraform_test_contract.iam.exact_relations)) && module.access_platform.terraform_test_contract.iam.custom_role.id == "accessSecretContainerAdmin" && !contains(toset(module.access_platform.terraform_test_contract.iam.custom_role.permissions), "secretmanager.versions.access") && !contains(toset(module.access_platform.terraform_test_contract.iam.custom_role.permissions), "secretmanager.versions.get")
    error_message = "The complete project IAM collection must retain only the reviewed management and runtime roles."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.iam.state_binding_count == 2 && toset(module.access_platform.terraform_test_contract.iam.state_binding_keys) == toset(["terraform-plan", "terraform-apply"]) && toset(module.access_platform.terraform_test_contract.iam.state_roles) == toset(["roles/storage.objectViewer", "roles/storage.objectAdmin"]) && alltrue(values(module.access_platform.terraform_test_contract.iam.exact_state_relations)) && module.access_platform.terraform_test_contract.iam.service_account_binding_count == (module.access_platform.database_name == "access_production" ? 9 : 8) && length([for role in module.access_platform.terraform_test_contract.iam.service_account_roles : role if role == "roles/iam.serviceAccountUser"]) == 3 && length([for role in module.access_platform.terraform_test_contract.iam.service_account_roles : role if role == "roles/iam.workloadIdentityUser"]) == (module.access_platform.database_name == "access_production" ? 6 : 5) && alltrue(values(module.access_platform.terraform_test_contract.iam.exact_deploy_relations))
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
    condition     = toset(keys(module.access_platform.terraform_test_contract.wif.provider_ids_by_identity)) == (module.access_platform.database_name == "access_production" ? toset(["terraform-plan", "terraform-apply", "deploy", "rollback", "admin-bootstrap", "access-release"]) : toset(["terraform-plan", "terraform-apply", "deploy", "rollback", "admin-bootstrap"])) && alltrue([for role in values(module.access_platform.terraform_test_contract.wif.impersonation_roles_by_identity) : role == "roles/iam.workloadIdentityUser"]) && toset(keys(module.access_platform.terraform_test_contract.iam.deploy_runtime_roles)) == toset(["api", "worker", "migration"]) && alltrue([for role in values(module.access_platform.terraform_test_contract.iam.deploy_runtime_roles) : role == "roles/iam.serviceAccountUser"])
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
}
