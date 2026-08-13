mock_provider "google" {}

run "private_platform_contract" {
  command = plan

  variables {
    project_id        = "slut-access-production-fixture"
    source_repository = "example.invalid/agency/prison-policy-ai"
    labels            = { fixture = "op03" }
  }

  assert {
    condition     = length(module.access_platform.secret_resource_ids) == 9
    error_message = "The platform must expose exactly nine secret containers."
  }

  assert {
    condition     = contains(["access_test", "access_production"], module.access_platform.database_name)
    error_message = "Each root must use one of the two isolated database names."
  }

  assert {
    condition = length([
      module.access_platform.terraform_plan_service_account_email,
      module.access_platform.terraform_apply_service_account_email,
      module.access_platform.deploy_service_account_email,
      module.access_platform.rollback_service_account_email,
      module.access_platform.admin_bootstrap_service_account_email,
    ]) == 5
    error_message = "Every environment needs five distinct non-release workflow identities."
  }

}
