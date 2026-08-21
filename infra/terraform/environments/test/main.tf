locals {
  workflow_prefix = "${var.source_repository}/.github/workflows"
  wif_trust = {
    terraform-plan = {
      github_environment = "test"
      workflow_refs      = ["${local.workflow_prefix}/terraform-plan.yml@${var.github_ref_pattern}"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = var.github_ref_pattern
    }
    terraform-apply = {
      github_environment = "test"
      workflow_refs      = ["${local.workflow_prefix}/terraform-apply.yml@${var.github_ref_pattern}"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = var.github_ref_pattern
    }
    deploy = {
      github_environment = "test"
      workflow_refs      = ["${local.workflow_prefix}/deploy-test.yml@${var.github_ref_pattern}"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = var.github_ref_pattern
    }
    rollback = {
      github_environment = "test"
      workflow_refs      = ["${local.workflow_prefix}/rollback-test.yml@${var.github_ref_pattern}"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = var.github_ref_pattern
    }
    admin-bootstrap = {
      github_environment = "test"
      workflow_refs      = ["${local.workflow_prefix}/bootstrap-first-admin.yml@${var.github_ref_pattern}"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = var.github_ref_pattern
    }
    access-release = {
      github_environment = "access-release"
      workflow_refs      = ["${local.workflow_prefix}/access-release.yml@${var.github_ref_pattern}"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = var.github_ref_pattern
    }
  }
}

module "access_platform" {
  source = "../../modules/access_platform"

  environment                       = var.environment
  project_id                        = var.project_id
  region                            = var.region
  network_name                      = var.network_name
  database_instance_name            = var.database_instance_name
  database_name                     = var.database_name
  sql_tier                          = var.sql_tier
  state_bucket_name                 = var.state_bucket_name
  github_repository                 = var.source_repository
  github_ref_pattern                = var.github_ref_pattern
  enable_access_release_identity    = false
  wif_trust                         = local.wif_trust
  storage_log_bucket_name           = var.storage_log_bucket_name
  artifact_registry_kms_key_name    = var.artifact_registry_kms_key_name
  labels                            = merge(var.labels, { system = "access" })
  image_digest                      = var.image_digest
  source_commit                     = var.source_commit
  release_version                   = var.release_version
  api_version                       = var.api_version
  latest_client_version             = var.latest_client_version
  minimum_client_version            = var.minimum_client_version
  minimum_server_version            = var.minimum_server_version
  release_notes                     = var.release_notes
  managed_hostname                  = var.managed_hostname
  dns_zone_name                     = var.dns_zone_name
  image_repository_id               = var.image_repository_id
  queue_max_attempts                = var.queue_max_attempts
  gcp_model_location                = var.gcp_model_location
  agent_builder_location            = var.agent_builder_location
  agent_builder_collection          = var.agent_builder_collection
  agent_builder_engine_id           = var.agent_builder_engine_id
  agent_builder_serving_config      = var.agent_builder_serving_config
  fast_model                        = var.fast_model
  pro_model                         = var.pro_model
  legacy_report_mode                = "disabled"
  review_object_prefix              = var.review_object_prefix
  log_level                         = var.log_level
  api_min_instances                 = var.api_min_instances
  api_max_instances                 = var.api_max_instances
  api_max_concurrency               = var.api_max_concurrency
  worker_min_instances              = var.worker_min_instances
  worker_max_instances              = var.worker_max_instances
  worker_max_concurrency            = var.worker_max_concurrency
  roster_source_uri                 = var.roster_source_uri
  roster_corrections_uri            = var.roster_corrections_uri
  roster_report_uri                 = var.roster_report_uri
  roster_expected_sha256            = var.roster_expected_sha256
  bootstrap_request_uri             = var.bootstrap_request_uri
  bootstrap_request_sha256          = var.bootstrap_request_sha256
  notification_channel_ids          = var.notification_channel_ids
  billing_account_id                = var.billing_account_id
  monthly_budget_amount             = var.monthly_budget_amount
  budget_pubsub_topic               = var.budget_pubsub_topic
  observability_owner_role          = var.observability_owner_role
  sensitive_log_scanner_metric_type = var.sensitive_log_scanner_metric_type
}
