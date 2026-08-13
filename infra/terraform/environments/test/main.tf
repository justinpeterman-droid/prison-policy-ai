module "access_platform" {
  source = "../../modules/access_platform"

  environment                       = var.environment
  project_id                        = var.project_id
  region                            = var.region
  network_name                      = "access-test-network"
  database_instance_name            = "access-test-postgres"
  database_name                     = "access_test"
  sql_tier                          = "db-custom-1-3840"
  github_repository                 = var.source_repository
  github_ref_pattern                = "refs/heads/main"
  enable_access_release_identity    = false
  state_bucket_name                 = var.state_bucket_name
  labels                            = merge(var.labels, { system = "access" })
  image_digest                      = "example.invalid/access/test@sha256:0000000000000000000000000000000000000000000000000000000000000000"
  source_commit                     = "0000000000000000000000000000000000000000"
  release_version                   = "development"
  api_version                       = "v1"
  latest_client_version             = "development"
  minimum_client_version            = "development"
  minimum_server_version            = "development"
  release_notes                     = "Development fixture release."
  managed_hostname                  = "test.example.invalid"
  dns_zone_name                     = "test-zone"
  image_repository_id               = "access-test-images"
  queue_max_attempts                = 5
  gcp_model_location                = "us-central1"
  agent_builder_location            = "global"
  agent_builder_collection          = "default_collection"
  agent_builder_engine_id           = "fixture-engine"
  agent_builder_serving_config      = "default_search"
  fast_model                        = "fixture-fast-model-pinned"
  pro_model                         = "fixture-pro-model-pinned"
  legacy_report_mode                = "disabled"
  review_object_prefix              = "review-lab/"
  log_level                         = "INFO"
  api_min_instances                 = 0
  api_max_instances                 = 10
  api_max_concurrency               = 20
  worker_min_instances              = 0
  worker_max_instances              = 10
  worker_max_concurrency            = 4
  roster_source_uri                 = "gs://access-test-roster/operator-supplied-roster.json"
  roster_corrections_uri            = "gs://access-test-roster/operator-supplied-corrections.json"
  roster_report_uri                 = "gs://access-test-roster/operator-supplied-report.json"
  roster_expected_sha256            = "0000000000000000000000000000000000000000000000000000000000000000"
  bootstrap_request_uri             = "gs://access-test-configuration/admin-bootstrap-requests/00000000-0000-4000-8000-000000000001.json"
  bootstrap_request_sha256          = "0000000000000000000000000000000000000000000000000000000000000000"
  notification_channel_ids          = []
  billing_account_id                = "fixture-billing-account"
  monthly_budget_amount             = 1
  budget_pubsub_topic               = "projects/${var.project_id}/topics/access-test-budget-alerts"
  observability_owner_role          = "platform-operations"
  sensitive_log_scanner_metric_type = "custom.googleapis.com/access_sensitive_log_scanner_failure"

  wif_trust = {
    terraform-plan = {
      github_environment = "test"
      workflow_refs      = ["${var.source_repository}/.github/workflows/terraform-plan.yml@refs/heads/main"]
      workflow_claims    = toset(["workflow_ref", "job_workflow_ref"])
      ref_pattern        = "refs/heads/main"
    }
    terraform-apply = {
      github_environment = "test"
      workflow_refs      = ["${var.source_repository}/.github/workflows/terraform-apply.yml@refs/heads/main"]
      workflow_claims    = toset(["job_workflow_ref"])
      ref_pattern        = "refs/heads/main"
    }
    deploy = {
      github_environment = "test"
      workflow_refs      = ["${var.source_repository}/.github/workflows/deploy-test.yml@refs/heads/main"]
      workflow_claims    = toset(["workflow_ref"])
      ref_pattern        = "refs/heads/main"
    }
    rollback = {
      github_environment = "test"
      workflow_refs      = ["${var.source_repository}/.github/workflows/rollback-test.yml@refs/heads/main"]
      workflow_claims    = toset(["workflow_ref"])
      ref_pattern        = "refs/heads/main"
    }
    admin-bootstrap = {
      github_environment = "test"
      workflow_refs      = ["${var.source_repository}/.github/workflows/bootstrap-first-admin.yml@refs/heads/main"]
      workflow_claims    = toset(["workflow_ref"])
      ref_pattern        = "refs/heads/main"
    }
    access-release = {
      github_environment = "access-release"
      workflow_refs      = ["${var.source_repository}/.github/workflows/access-release.yml@refs/heads/main"]
      workflow_claims    = toset(["workflow_ref"])
      ref_pattern        = "refs/heads/main"
    }
  }
}
