variable "environment" {
  description = "Environment managed by this module."
  type        = string

  validation {
    condition     = contains(["test", "production"], var.environment)
    error_message = "environment must be test or production."
  }
}

variable "project_id" {
  description = "Dedicated Google Cloud project for this environment."
  type        = string
  nullable    = false
}

variable "region" {
  description = "Primary regional location."
  type        = string
  default     = "us-central1"
}

variable "network_name" {
  description = "Custom VPC name for the environment."
  type        = string
  nullable    = false
}

variable "database_instance_name" {
  description = "Private Cloud SQL instance name."
  type        = string
  nullable    = false
}

variable "database_name" {
  description = "Application database name."
  type        = string
  nullable    = false
}

variable "sql_tier" {
  description = "Cloud SQL machine tier selected through the external capacity review."
  type        = string
  nullable    = false
}

variable "state_bucket_name" {
  description = "Environment-specific Terraform state bucket supplied externally."
  type        = string
  nullable    = false
}

variable "github_repository" {
  description = "Exact owner/repository trusted by workload identity federation."
  type        = string
  nullable    = false
}

variable "github_ref_pattern" {
  description = "Exact protected Git ref accepted by credentialed workflows."
  type        = string
  default     = "refs/heads/main"
}

variable "enable_access_release_identity" {
  description = "Create the production-only Access release workflow identity."
  type        = bool
  default     = false
}

variable "storage_log_bucket_name" {
  description = "Externally provisioned bucket that receives Cloud Storage access logs."
  type        = string
  nullable    = false

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]$", var.storage_log_bucket_name))
    error_message = "storage_log_bucket_name must be a provider-valid bucket name."
  }
}

variable "artifact_registry_kms_key_name" {
  description = "Externally provisioned KMS key name reserved for Artifact Registry encryption."
  type        = string
  nullable    = false

  validation {
    condition     = length(trimspace(var.artifact_registry_kms_key_name)) > 0
    error_message = "artifact_registry_kms_key_name must be supplied by the external encryption key owner."
  }
}

variable "wif_trust" {
  description = "Exact workflow, environment, claim, and ref trust contract for each workflow identity."
  type = map(object({
    github_environment = string
    workflow_refs      = set(string)
    workflow_claim     = string
    ref_pattern        = string
  }))

  validation {
    condition = toset(keys(var.wif_trust)) == toset([
      "terraform-plan",
      "terraform-apply",
      "deploy",
      "rollback",
      "admin-bootstrap",
      "access-release",
    ])
    error_message = "wif_trust must define exactly the six approved workflow identities."
  }

  validation {
    condition = alltrue([
      for trust in values(var.wif_trust) : contains(["workflow_ref", "job_workflow_ref"], trust.workflow_claim)
    ])
    error_message = "workflow_claim must be workflow_ref or job_workflow_ref."
  }

  validation {
    condition = alltrue([
      for trust in values(var.wif_trust) : trust.ref_pattern == var.github_ref_pattern
    ])
    error_message = "Every WIF trust entry must use the protected github_ref_pattern."
  }
}

variable "labels" {
  description = "Non-sensitive labels applied to supported resources."
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for key, value in var.labels :
      can(regex("^[a-z][a-z0-9_-]{0,62}$", key)) &&
      can(regex("^[a-z0-9_-]{0,63}$", value)) &&
      !contains(toset(["source", "release", "image_digest"]), key) &&
      !can(regex("(?i)(secret|token|password|passwd|credential|authorization|bearer|api[_-]?key|private[_-]?key|access[_-]?code|admin[_-]?code|pin)", key)) &&
      !can(regex("(?i)(secret|token|password|passwd|credential|authorization|bearer|api[_-]?key|private[_-]?key|access[_-]?code|admin[_-]?code|pin)", value))
    ])
    error_message = "labels must use provider-safe non-sensitive key/value syntax and cannot override source, release, or image_digest stamps."
  }
}

variable "notification_channel_ids" {
  type    = set(string)
  default = []
}
variable "billing_account_id" {
  description = "Externally authorized billing account for this environment; never commit an account value."
  type        = string
  validation {
    condition     = length(trimspace(var.billing_account_id)) > 0
    error_message = "billing_account_id must be supplied from the external billing authorization gate."
  }
}
variable "monthly_budget_amount" {
  description = "Externally approved monthly USD budget amount."
  type        = number
  validation {
    condition     = var.monthly_budget_amount > 0
    error_message = "monthly_budget_amount must be a positive externally approved amount."
  }
}
variable "budget_pubsub_topic" {
  description = "Externally approved Pub/Sub topic used for budget routing."
  type        = string
  validation {
    condition     = can(regex("^projects/[^/]+/topics/[^/]+$", var.budget_pubsub_topic))
    error_message = "budget_pubsub_topic must be a full projects/.../topics/... resource name."
  }
}
variable "observability_owner_role" {
  description = "Role, not a person or contact destination, responsible for alert triage."
  type        = string
  validation {
    condition     = length(trimspace(var.observability_owner_role)) > 0 && !can(regex("(?i)(@|https?://|token|secret|pin)", var.observability_owner_role))
    error_message = "observability_owner_role must be a non-sensitive owner role, not contact or credential data."
  }
}
variable "sensitive_log_scanner_metric_type" {
  description = "Externally confirmed metric emitted only when the sensitive-log scanner fails; production gate remains closed until supplied."
  type        = string
  validation {
    condition     = can(regex("^(logging.googleapis.com/user|custom.googleapis.com)/[a-z][a-z0-9_/.-]{0,199}$", var.sensitive_log_scanner_metric_type))
    error_message = "sensitive_log_scanner_metric_type must be an externally confirmed bounded Google Monitoring metric type."
  }
}

variable "image_digest" {
  type        = string
  description = "Artifact Registry image reference pinned by sha256 digest."

  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.image_digest))
    error_message = "image_digest must be an Artifact Registry reference ending in an immutable sha256 digest."
  }
}

variable "source_commit" {
  type = string
  validation {
    condition     = can(regex("^[0-9a-f]{40}$", var.source_commit)) && (var.environment == "test" || var.source_commit != "0000000000000000000000000000000000000000")
    error_message = "source_commit must be a 40-character lowercase hexadecimal revision."
  }
}
variable "release_version" {
  type = string
  validation {
    condition     = can(regex("^(development|v?[0-9]+\\.[0-9]+\\.[0-9]+([-.+][0-9A-Za-z.-]+)?)$", var.release_version))
    error_message = "release_version must be SemVer or development."
  }
}
variable "api_version" {
  type = string
  validation {
    condition     = var.api_version == "v1"
    error_message = "api_version must be v1."
  }
}
variable "latest_client_version" {
  type = string
  validation {
    condition     = can(regex("^(development|v?[0-9]+\\.[0-9]+\\.[0-9]+([-.+][0-9A-Za-z.-]+)?)$", var.latest_client_version))
    error_message = "latest_client_version must be SemVer or development."
  }
}
variable "minimum_client_version" {
  type = string
  validation {
    condition     = can(regex("^(development|v?[0-9]+\\.[0-9]+\\.[0-9]+([-.+][0-9A-Za-z.-]+)?)$", var.minimum_client_version))
    error_message = "minimum_client_version must be SemVer or development."
  }
}
variable "minimum_server_version" {
  type = string
  validation {
    condition     = can(regex("^(development|v?[0-9]+\\.[0-9]+\\.[0-9]+([-.+][0-9A-Za-z.-]+)?)$", var.minimum_server_version))
    error_message = "minimum_server_version must be SemVer or development."
  }
}
variable "release_notes" {
  type = string
  validation {
    condition     = length(var.release_notes) >= 1 && length(var.release_notes) <= 500 && !can(regex("[\\r\\n[:cntrl:]]", var.release_notes))
    error_message = "release_notes must be one line of 1-500 printable characters."
  }
}

variable "managed_hostname" { type = string }
variable "dns_zone_name" { type = string }
variable "image_repository_id" { type = string }
variable "queue_max_attempts" { type = number }
variable "queue_max_concurrent_dispatches" {
  type    = number
  default = 4
}
variable "queue_max_dispatches_per_second" {
  type    = number
  default = 4
}
variable "gcp_model_location" { type = string }
variable "agent_builder_location" { type = string }
variable "agent_builder_collection" { type = string }
variable "agent_builder_engine_id" { type = string }
variable "agent_builder_serving_config" { type = string }
variable "fast_model" { type = string }
variable "pro_model" { type = string }
variable "legacy_report_mode" { type = string }
variable "review_object_prefix" { type = string }
variable "log_level" { type = string }
variable "api_min_instances" { type = number }
variable "api_max_instances" { type = number }
variable "api_max_concurrency" { type = number }
variable "worker_min_instances" { type = number }
variable "worker_max_instances" { type = number }
variable "worker_max_concurrency" { type = number }
variable "roster_source_uri" {
  type = string
  validation {
    condition     = can(regex("^gs://access-(test|production)-roster/[A-Za-z0-9][A-Za-z0-9._/-]{0,500}$", var.roster_source_uri)) && startswith(var.roster_source_uri, "gs://access-${var.environment}-roster/") && !strcontains(var.roster_source_uri, "..")
    error_message = "roster_source_uri must identify one private environment roster-bucket object."
  }
}
variable "roster_corrections_uri" {
  type = string
  validation {
    condition     = can(regex("^gs://access-(test|production)-roster/[A-Za-z0-9][A-Za-z0-9._/-]{0,500}$", var.roster_corrections_uri)) && startswith(var.roster_corrections_uri, "gs://access-${var.environment}-roster/") && !strcontains(var.roster_corrections_uri, "..")
    error_message = "roster_corrections_uri must identify one private environment roster-bucket object."
  }
}
variable "roster_report_uri" {
  type = string
  validation {
    condition     = can(regex("^gs://access-(test|production)-roster/[A-Za-z0-9][A-Za-z0-9._/-]{0,500}$", var.roster_report_uri)) && startswith(var.roster_report_uri, "gs://access-${var.environment}-roster/") && !strcontains(var.roster_report_uri, "..") && var.roster_report_uri != var.roster_source_uri && var.roster_report_uri != var.roster_corrections_uri
    error_message = "roster_report_uri must identify one private environment roster-bucket object."
  }
}
variable "roster_expected_sha256" {
  type = string
  validation {
    condition     = can(regex("^[0-9a-f]{64}$", var.roster_expected_sha256))
    error_message = "roster_expected_sha256 must be lowercase 64-hex."
  }
}
variable "bootstrap_request_uri" {
  type = string
  validation {
    condition     = can(regex("^gs://access-(test|production)-configuration/admin-bootstrap-requests/[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\\.json$", var.bootstrap_request_uri)) && startswith(var.bootstrap_request_uri, "gs://access-${var.environment}-configuration/admin-bootstrap-requests/")
    error_message = "bootstrap_request_uri must be an opaque v4 UUID object in the private bootstrap request prefix."
  }
}
variable "bootstrap_request_sha256" {
  type = string
  validation {
    condition     = can(regex("^[0-9a-f]{64}$", var.bootstrap_request_sha256))
    error_message = "bootstrap_request_sha256 must be lowercase 64-hex."
  }
}
