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
    condition = module.access_platform.terraform_test_contract.service_account_count == (
      module.access_platform.database_name == "access_production" ? 11 : 10
    ) && alltrue([for id_length in module.access_platform.terraform_test_contract.service_account_id_lengths : id_length <= 30])
    error_message = "Test and production must have exactly ten and eleven provider-valid service accounts."
  }

  assert {
    condition = module.access_platform.terraform_test_contract.wif_provider_count == (
      module.access_platform.database_name == "access_production" ? 6 : 5
    ) && alltrue([for id_length in module.access_platform.terraform_test_contract.wif_provider_id_lengths : id_length <= 32])
    error_message = "Test and production must expose five and six provider-valid WIF identities."
  }

  assert {
    condition = length(setsubtract(toset(module.access_platform.terraform_test_contract.secret_names), toset([
      "access-database-url", "identity-hash-pepper", "cursor-signing-key",
      "client-update-grant-key", "legacy-access-code", "legacy-admin-code",
      "github-feedback-token", "flask-session-secret", "initial-admin-pin",
      ]))) == 0 && length(setsubtract(toset([
      "access-database-url", "identity-hash-pepper", "cursor-signing-key",
      "client-update-grant-key", "legacy-access-code", "legacy-admin-code",
      "github-feedback-token", "flask-session-secret", "initial-admin-pin",
    ]), toset(module.access_platform.terraform_test_contract.secret_names))) == 0 && module.access_platform.terraform_test_contract.secret_version_resource_count == 0
    error_message = "Only the nine approved empty secret containers may exist; Terraform must not create secret versions."
  }

  assert {
    condition     = module.access_platform.terraform_test_contract.update_grant.accessor_category == "api" && module.access_platform.terraform_test_contract.update_grant.accessor_role == "roles/secretmanager.secretAccessor" && module.access_platform.terraform_test_contract.update_grant.non_api_accessor_count == 0 && module.access_platform.terraform_test_contract.bootstrap.database_accessor_role == "roles/secretmanager.secretAccessor" && module.access_platform.terraform_test_contract.bootstrap.initial_pin_adder_role == "roles/secretmanager.secretVersionAdder" && module.access_platform.terraform_test_contract.bootstrap.initial_pin_accessor_count == 0 && module.access_platform.terraform_test_contract.workflow_secret_accessor_count == 0
    error_message = "Update-grant, bootstrap PIN, and workflow secret-access boundaries must remain least privilege."
  }

  assert {
    condition     = module.access_platform.database_name == "access_test" ? module.access_platform.terraform_test_contract.bootstrap.environment == "test" : module.access_platform.terraform_test_contract.bootstrap.environment == "production-deploy"
    error_message = "Bootstrap trust must use test or production-deploy for its matching root."
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
