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
    condition     = length(module.access_platform.secret_resource_ids) == 9
    error_message = "The platform must expose exactly nine secret containers."
  }

  assert {
    condition = length(setsubtract(toset(keys(module.access_platform.secret_resource_ids)), toset([
      "access-database-url", "identity-hash-pepper", "cursor-signing-key",
      "client-update-grant-key", "legacy-access-code", "legacy-admin-code",
      "github-feedback-token", "flask-session-secret", "initial-admin-pin",
      ]))) == 0 && length(setsubtract(toset([
      "access-database-url", "identity-hash-pepper", "cursor-signing-key",
      "client-update-grant-key", "legacy-access-code", "legacy-admin-code",
      "github-feedback-token", "flask-session-secret", "initial-admin-pin",
    ]), toset(keys(module.access_platform.secret_resource_ids)))) == 0
    error_message = "The platform must define exactly the nine approved secret containers."
  }

  assert {
    condition     = contains(["access_test", "access_production"], module.access_platform.database_name)
    error_message = "Each root must use one of the two isolated database names."
  }

  assert {
    condition = alltrue([
      strcontains(file("${path.root}/../../modules/access_platform/sql.tf"), "database_version"),
      strcontains(file("${path.root}/../../modules/access_platform/sql.tf"), "POSTGRES_17"),
      strcontains(file("${path.root}/../../modules/access_platform/sql.tf"), "availability_type"),
      strcontains(file("${path.root}/../../modules/access_platform/sql.tf"), "REGIONAL"),
      strcontains(file("${path.root}/../../modules/access_platform/sql.tf"), "deletion_protection"),
      strcontains(file("${path.root}/../../modules/access_platform/sql.tf"), "var.environment == \"production\""),
    ])
    error_message = "The module must preserve PostgreSQL 17 plus production HA and deletion protection."
  }

  assert {
    condition = alltrue([
      strcontains(file("${path.root}/../../modules/access_platform/identities.tf"), "api             = \"api\""),
      strcontains(file("${path.root}/../../modules/access_platform/identities.tf"), "worker          = \"worker\""),
      strcontains(file("${path.root}/../../modules/access_platform/identities.tf"), "task_invoker    = \"task-invoker\""),
      strcontains(file("${path.root}/../../modules/access_platform/identities.tf"), "migration       = \"migration\""),
      strcontains(file("${path.root}/../../modules/access_platform/identities.tf"), "bootstrap       = \"bootstrap\""),
      strcontains(file("${path.root}/../../modules/access_platform/identities.tf"), "terraform_plan  = \"tf-plan\""),
      strcontains(file("${path.root}/../../modules/access_platform/identities.tf"), "terraform_apply = \"tf-apply\""),
      strcontains(file("${path.root}/../../modules/access_platform/identities.tf"), "deploy          = \"deploy\""),
      strcontains(file("${path.root}/../../modules/access_platform/identities.tf"), "rollback        = \"rollback\""),
      strcontains(file("${path.root}/../../modules/access_platform/identities.tf"), "admin_bootstrap = \"admin-bootstrap\""),
      strcontains(file("${path.root}/../../modules/access_platform/identities.tf"), "access_release  = \"release\""),
      strcontains(file("${path.root}/../../modules/access_platform/identities.tf"), "logical_name != \"access_release\" || var.enable_access_release_identity"),
      module.access_platform.database_name == "access_test" ? strcontains(file("${path.root}/main.tf"), "enable_access_release_identity = false") : strcontains(file("${path.root}/main.tf"), "enable_access_release_identity = true"),
    ])
    error_message = "Test must expose ten identities and production eleven, with release production-only."
  }

  assert {
    condition = alltrue([
      strcontains(file("${path.root}/../../modules/access_platform/outputs.tf"), "output \"terraform_plan_wif_provider_name\""),
      strcontains(file("${path.root}/../../modules/access_platform/outputs.tf"), "output \"terraform_apply_wif_provider_name\""),
      strcontains(file("${path.root}/../../modules/access_platform/outputs.tf"), "output \"deploy_wif_provider_name\""),
      strcontains(file("${path.root}/../../modules/access_platform/outputs.tf"), "output \"rollback_wif_provider_name\""),
      strcontains(file("${path.root}/../../modules/access_platform/outputs.tf"), "output \"admin_bootstrap_wif_provider_name\""),
      strcontains(file("${path.root}/../../modules/access_platform/outputs.tf"), "output \"access_release_wif_provider_name\""),
      strcontains(file("${path.root}/../../modules/access_platform/outputs.tf"), "try(google_iam_workload_identity_pool_provider.workflow[\"access-release\"].name, null)"),
    ])
    error_message = "The native contract must retain five WIF outputs plus the production-only release output."
  }

  assert {
    condition = alltrue([
      strcontains(file("${path.root}/../../modules/access_platform/identities.tf"), "google_secret_manager_secret_iam_member\" \"api_client_update_grant_key"),
      strcontains(file("${path.root}/../../modules/access_platform/identities.tf"), "google_service_account.identities[\"api\"].member"),
      strcontains(file("${path.root}/../../modules/access_platform/identities.tf"), "google_secret_manager_secret_iam_member\" \"bootstrap_initial_pin_adder"),
      strcontains(file("${path.root}/../../modules/access_platform/identities.tf"), "roles/secretmanager.secretVersionAdder"),
      strcontains(file("${path.root}/main.tf"), "bootstrap-first-admin.yml@refs/heads/main"),
      strcontains(file("${path.root}/main.tf"), "workflow_claims    = toset([\"workflow_ref\"])"),
    ])
    error_message = "Update-grant and bootstrap secret boundaries plus bootstrap top-level trust must remain explicit."
  }

}
