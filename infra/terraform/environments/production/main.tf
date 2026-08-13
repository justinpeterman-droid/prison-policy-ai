locals {
  workflow_prefix = "${var.source_repository}/.github/workflows"
  wif_trust = {
    terraform-plan = {
      github_environment = "production-plan"
      workflow_refs      = ["${local.workflow_prefix}/terraform-plan.yml@${var.github_ref_pattern}"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = var.github_ref_pattern
    }
    terraform-apply = {
      github_environment = "production-apply"
      workflow_refs      = ["${local.workflow_prefix}/terraform-apply.yml@${var.github_ref_pattern}"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = var.github_ref_pattern
    }
    deploy = {
      github_environment = "production-deploy"
      workflow_refs      = ["${local.workflow_prefix}/deploy-production.yml@${var.github_ref_pattern}"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = var.github_ref_pattern
    }
    rollback = {
      github_environment = "production-rollback"
      workflow_refs      = ["${local.workflow_prefix}/rollback-production.yml@${var.github_ref_pattern}"]
      workflow_claim     = "workflow_ref"
      ref_pattern        = var.github_ref_pattern
    }
    admin-bootstrap = {
      github_environment = "production-deploy"
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

variable "roster_source_uri" {
  description = "Protected operator-supplied private roster object for this approved production run."
  type        = string
  validation {
    condition     = can(regex("^gs://access-production-roster/[A-Za-z0-9][A-Za-z0-9._/-]{0,500}$", var.roster_source_uri)) && !strcontains(var.roster_source_uri, "..")
    error_message = "roster_source_uri must identify one private production roster object."
  }
}

variable "roster_corrections_uri" {
  description = "Protected operator-supplied corrections object for this approved production run."
  type        = string
  validation {
    condition     = can(regex("^gs://access-production-roster/[A-Za-z0-9][A-Za-z0-9._/-]{0,500}$", var.roster_corrections_uri)) && !strcontains(var.roster_corrections_uri, "..")
    error_message = "roster_corrections_uri must identify one private production roster object."
  }
}

variable "roster_report_uri" {
  description = "Protected operator-supplied immutable report object for this approved production run."
  type        = string
  validation {
    condition     = can(regex("^gs://access-production-roster/[A-Za-z0-9][A-Za-z0-9._/-]{0,500}$", var.roster_report_uri)) && !strcontains(var.roster_report_uri, "..")
    error_message = "roster_report_uri must identify one private production roster report object."
  }
}

variable "roster_expected_sha256" {
  description = "Externally approved SHA-256 for the exact production roster bytes."
  type        = string
  validation {
    condition     = can(regex("^[0-9a-f]{64}$", var.roster_expected_sha256)) && var.roster_expected_sha256 != strrep("0", 64)
    error_message = "roster_expected_sha256 must be a non-placeholder lowercase SHA-256."
  }
}

variable "bootstrap_request_uri" {
  description = "Protected opaque private request object approved for the one-time production bootstrap."
  type        = string
  validation {
    condition     = can(regex("^gs://access-production-configuration/admin-bootstrap-requests/[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\\.json$", var.bootstrap_request_uri))
    error_message = "bootstrap_request_uri must be an opaque v4 UUID object in the private production prefix."
  }
}

variable "bootstrap_request_sha256" {
  description = "Externally approved SHA-256 for the exact immutable bootstrap request bytes."
  type        = string
  validation {
    condition     = can(regex("^[0-9a-f]{64}$", var.bootstrap_request_sha256)) && var.bootstrap_request_sha256 != strrep("0", 64)
    error_message = "bootstrap_request_sha256 must be a non-placeholder lowercase SHA-256."
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
  enable_access_release_identity    = true
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
  legacy_report_mode                = var.legacy_report_mode
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
