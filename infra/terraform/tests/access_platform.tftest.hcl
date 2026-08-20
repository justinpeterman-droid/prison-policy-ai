mock_provider "google" {
  override_during = plan
}

run "test_environment_contract" {
  command = plan

  module {
    source = "../../modules/access_platform"
  }

  variables {
    environment                    = "test"
    project_id                     = "slut-access-production-fixture"
    region                         = "us-central1"
    network_name                   = "access-test-fixture"
    database_instance_name         = "access-test-postgres-fixture"
    database_name                  = "access_fixture"
    sql_tier                       = "db-custom-1-3840"
    state_bucket_name              = "slut-access-production-fixture-test-state"
    github_repository              = "example.invalid/agency/prison-policy-ai"
    github_ref_pattern             = "refs/heads/main"
    enable_access_release_identity = false
    labels                         = { data_class = "fictional" }
    wif_trust = {
      terraform-plan = {
        github_environment = "test"
        workflow_refs      = ["example.invalid/agency/prison-policy-ai/.github/workflows/terraform-plan.yml@refs/heads/main"]
        workflow_claim     = "workflow_ref"
        ref_pattern        = "refs/heads/main"
      }
      terraform-apply = {
        github_environment = "test"
        workflow_refs      = ["example.invalid/agency/prison-policy-ai/.github/workflows/terraform-apply.yml@refs/heads/main"]
        workflow_claim     = "workflow_ref"
        ref_pattern        = "refs/heads/main"
      }
      deploy = {
        github_environment = "test"
        workflow_refs      = ["example.invalid/agency/prison-policy-ai/.github/workflows/deploy-test.yml@refs/heads/main"]
        workflow_claim     = "workflow_ref"
        ref_pattern        = "refs/heads/main"
      }
      rollback = {
        github_environment = "test"
        workflow_refs      = ["example.invalid/agency/prison-policy-ai/.github/workflows/rollback-test.yml@refs/heads/main"]
        workflow_claim     = "workflow_ref"
        ref_pattern        = "refs/heads/main"
      }
      admin-bootstrap = {
        github_environment = "test"
        workflow_refs      = ["example.invalid/agency/prison-policy-ai/.github/workflows/bootstrap-first-admin.yml@refs/heads/main"]
        workflow_claim     = "workflow_ref"
        ref_pattern        = "refs/heads/main"
      }
      access-release = {
        github_environment = "access-release"
        workflow_refs      = ["example.invalid/agency/prison-policy-ai/.github/workflows/access-release.yml@refs/heads/main"]
        workflow_claim     = "workflow_ref"
        ref_pattern        = "refs/heads/main"
      }
    }
  }

  assert {
    condition     = google_sql_database_instance.postgres.database_version == "POSTGRES_17"
    error_message = "Test must use PostgreSQL 17."
  }

  assert {
    condition     = google_sql_database_instance.postgres.settings[0].availability_type == "ZONAL" && !google_sql_database_instance.postgres.deletion_protection
    error_message = "Test SQL must be zonal and independently disposable."
  }

  assert {
    condition     = length(google_service_account.workflow) == 5
    error_message = "Test must have five workflow identities and no release identity."
  }

  assert {
    condition = length(toset([
      google_service_account.api.account_id,
      google_service_account.worker.account_id,
      google_service_account.task_invoker.account_id,
      google_service_account.migration.account_id,
      google_service_account.bootstrap.account_id,
    ])) == 5 && length(google_service_account.workflow) == 5
    error_message = "Test must define five distinct runtime and five workflow identities."
  }

  assert {
    condition     = length(google_iam_workload_identity_pool_provider.github) == 5 && !contains(keys(google_iam_workload_identity_pool_provider.github), "access-release")
    error_message = "Test must expose five WIF providers and no release provider."
  }

  assert {
    condition     = length(output.secret_resource_ids) == 9 && contains(keys(output.secret_resource_ids), "identity_hash_pepper") && contains(keys(output.secret_resource_ids), "cursor_signing_key") && contains(keys(output.secret_resource_ids), "client_update_grant_key") && contains(keys(output.secret_resource_ids), "initial_admin_pin")
    error_message = "Exactly nine required empty secret containers must exist."
  }

  assert {
    condition     = google_secret_manager_secret_iam_member.bootstrap_initial_pin_adder.role == "roles/secretmanager.secretVersionAdder"
    error_message = "Bootstrap runtime may add but not read the initial PIN version."
  }

  assert {
    condition     = google_secret_manager_secret_iam_member.api_client_update_grant_key.role == "roles/secretmanager.secretAccessor"
    error_message = "The API identity must be the accessor for the client update grant key."
  }

  assert {
    condition     = var.wif_trust["admin-bootstrap"].github_environment == "test"
    error_message = "Test bootstrap WIF must require the test environment."
  }
}

run "production_environment_contract" {
  command = plan

  module {
    source = "../../modules/access_platform"
  }

  variables {
    environment                    = "production"
    project_id                     = "slut-access-production-fixture"
    region                         = "us-central1"
    network_name                   = "access-production-fixture"
    database_instance_name         = "access-production-postgres-fixture"
    database_name                  = "access_fixture"
    sql_tier                       = "db-custom-2-7680"
    state_bucket_name              = "slut-access-production-fixture-production-state"
    github_repository              = "example.invalid/agency/prison-policy-ai"
    github_ref_pattern             = "refs/heads/main"
    enable_access_release_identity = true
    labels                         = { data_class = "fictional" }
    wif_trust = {
      terraform-plan = {
        github_environment = "production-plan"
        workflow_refs      = ["example.invalid/agency/prison-policy-ai/.github/workflows/terraform-plan.yml@refs/heads/main"]
        workflow_claim     = "workflow_ref"
        ref_pattern        = "refs/heads/main"
      }
      terraform-apply = {
        github_environment = "production-apply"
        workflow_refs      = ["example.invalid/agency/prison-policy-ai/.github/workflows/terraform-apply.yml@refs/heads/main"]
        workflow_claim     = "workflow_ref"
        ref_pattern        = "refs/heads/main"
      }
      deploy = {
        github_environment = "production-deploy"
        workflow_refs      = ["example.invalid/agency/prison-policy-ai/.github/workflows/deploy-production.yml@refs/heads/main"]
        workflow_claim     = "workflow_ref"
        ref_pattern        = "refs/heads/main"
      }
      rollback = {
        github_environment = "production-rollback"
        workflow_refs      = ["example.invalid/agency/prison-policy-ai/.github/workflows/rollback-production.yml@refs/heads/main"]
        workflow_claim     = "workflow_ref"
        ref_pattern        = "refs/heads/main"
      }
      admin-bootstrap = {
        github_environment = "production-deploy"
        workflow_refs      = ["example.invalid/agency/prison-policy-ai/.github/workflows/bootstrap-first-admin.yml@refs/heads/main"]
        workflow_claim     = "workflow_ref"
        ref_pattern        = "refs/heads/main"
      }
      access-release = {
        github_environment = "access-release"
        workflow_refs      = ["example.invalid/agency/prison-policy-ai/.github/workflows/access-release.yml@refs/heads/main"]
        workflow_claim     = "workflow_ref"
        ref_pattern        = "refs/heads/main"
      }
    }
  }

  assert {
    condition     = google_sql_database_instance.postgres.settings[0].availability_type == "REGIONAL" && google_sql_database_instance.postgres.deletion_protection
    error_message = "Production SQL must be regional and deletion-protected."
  }

  assert {
    condition     = length(google_service_account.workflow) == 6
    error_message = "Production must have six workflow identities including release."
  }

  assert {
    condition = length(toset([
      google_service_account.api.account_id,
      google_service_account.worker.account_id,
      google_service_account.task_invoker.account_id,
      google_service_account.migration.account_id,
      google_service_account.bootstrap.account_id,
    ])) == 5 && length(google_service_account.workflow) == 6
    error_message = "Production must define five distinct runtime and six workflow identities."
  }

  assert {
    condition     = length(google_iam_workload_identity_pool_provider.github) == 6 && contains(keys(google_iam_workload_identity_pool_provider.github), "access-release")
    error_message = "Production must expose all six WIF providers."
  }

  assert {
    condition     = var.wif_trust["admin-bootstrap"].github_environment == "production-deploy"
    error_message = "Production bootstrap WIF must require production-deploy."
  }
}
