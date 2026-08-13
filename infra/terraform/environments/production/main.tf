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
  image_digest                   = var.image_digest
  source_commit                  = var.source_commit
  release_version                = var.release_version
  api_version                    = var.api_version
  latest_client_version          = var.latest_client_version
  minimum_client_version         = var.minimum_client_version
  minimum_server_version         = var.minimum_server_version
  release_notes                  = var.release_notes
  managed_hostname               = var.managed_hostname
  dns_zone_name                  = var.dns_zone_name
  image_repository_id            = var.image_repository_id
  queue_max_attempts             = var.queue_max_attempts
  gcp_model_location             = var.gcp_model_location
  agent_builder_location         = var.agent_builder_location
  agent_builder_collection       = var.agent_builder_collection
  agent_builder_engine_id        = var.agent_builder_engine_id
  agent_builder_serving_config   = var.agent_builder_serving_config
  fast_model                     = var.fast_model
  pro_model                      = var.pro_model
  legacy_report_mode             = var.legacy_report_mode
  review_object_prefix           = var.review_object_prefix
  log_level                      = var.log_level
  api_min_instances              = var.api_min_instances
  api_max_instances              = var.api_max_instances
  api_max_concurrency            = var.api_max_concurrency
  worker_min_instances           = var.worker_min_instances
  worker_max_instances           = var.worker_max_instances
  worker_max_concurrency         = var.worker_max_concurrency

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
