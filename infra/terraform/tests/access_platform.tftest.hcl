mock_provider "google" {}

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
    ) && module.access_platform.terraform_test_contract.wif.distinct_provider_id_count == module.access_platform.terraform_test_contract.wif.provider_count && module.access_platform.terraform_test_contract.wif.impersonation_binding_count == module.access_platform.terraform_test_contract.wif.provider_count && module.access_platform.terraform_test_contract.wif.provider_specific_binding_count == module.access_platform.terraform_test_contract.wif.provider_count && module.access_platform.terraform_test_contract.wif.pool_id_length <= 32 && alltrue([for id_length in module.access_platform.terraform_test_contract.wif.provider_id_lengths : id_length <= 32]) && module.access_platform.terraform_test_contract.wif.direct_claim_condition_count == module.access_platform.terraform_test_contract.wif.provider_count
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
    condition     = module.access_platform.terraform_test_contract.secrets.binding_count == 12 && module.access_platform.terraform_test_contract.secrets.update_grant.role == "roles/secretmanager.secretAccessor" && module.access_platform.terraform_test_contract.secrets.bootstrap.database_role == "roles/secretmanager.secretAccessor" && module.access_platform.terraform_test_contract.secrets.bootstrap.pin_role == "roles/secretmanager.secretVersionAdder"
    error_message = "Update-grant, bootstrap PIN, and workflow secret-access boundaries must remain least privilege."
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
