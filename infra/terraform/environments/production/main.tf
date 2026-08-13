module "access_platform" {
  source = "../../modules/access_platform"

  environment                    = var.environment
  project_id                     = var.project_id
  region                         = "us-central1"
  network_name                   = "access-production-network"
  database_instance_name         = "access-production-postgres"
  database_name                  = "access_production"
  sql_tier                       = "db-custom-2-7680"
  github_repository              = var.source_repository
  github_ref_pattern             = "refs/heads/main"
  enable_access_release_identity = true
  state_bucket_name              = var.state_bucket_name
  labels                         = merge(var.labels, { system = "access" })
  image_digest                   = "example.invalid/access/production@sha256:0000000000000000000000000000000000000000000000000000000000000000"
  source_commit                  = "0000000000000000000000000000000000000000"
  release_version                = "development"
  api_version                    = "v1"
  latest_client_version          = "development"
  minimum_client_version         = "development"
  minimum_server_version         = "development"
  release_notes                  = "Development fixture release."
  managed_hostname               = "production.example.invalid"
  dns_zone_name                  = "production-zone"
  image_repository_id            = "access-production-images"
  queue_max_attempts             = 5
  gcp_model_location             = "us-central1"
  agent_builder_location         = "global"
  agent_builder_collection       = "default_collection"
  agent_builder_engine_id        = "fixture-engine"
  agent_builder_serving_config   = "default_search"
  fast_model                     = "fixture-fast-model-pinned"
  pro_model                      = "fixture-pro-model-pinned"
  legacy_report_mode             = "disabled"
  review_object_prefix           = "review-lab/"
  log_level                      = "INFO"
  api_min_instances              = 1
  api_max_instances              = 10
  api_max_concurrency            = 20
  worker_min_instances           = 0
  worker_max_instances           = 10
  worker_max_concurrency         = 4

  wif_trust = {
    terraform-plan = {
      github_environment = "production-plan"
      workflow_refs      = ["${var.source_repository}/.github/workflows/terraform-plan.yml@refs/heads/main"]
      workflow_claims    = toset(["workflow_ref", "job_workflow_ref"])
      ref_pattern        = "refs/heads/main"
    }
    terraform-apply = {
      github_environment = "production-apply"
      workflow_refs      = ["${var.source_repository}/.github/workflows/terraform-apply.yml@refs/heads/main"]
      workflow_claims    = toset(["job_workflow_ref"])
      ref_pattern        = "refs/heads/main"
    }
    deploy = {
      github_environment = "production-deploy"
      workflow_refs      = ["${var.source_repository}/.github/workflows/deploy-production.yml@refs/heads/main"]
      workflow_claims    = toset(["workflow_ref"])
      ref_pattern        = "refs/heads/main"
    }
    rollback = {
      github_environment = "production-rollback"
      workflow_refs      = ["${var.source_repository}/.github/workflows/rollback-production.yml@refs/heads/main"]
      workflow_claims    = toset(["workflow_ref"])
      ref_pattern        = "refs/heads/main"
    }
    admin-bootstrap = {
      github_environment = "production-deploy"
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
