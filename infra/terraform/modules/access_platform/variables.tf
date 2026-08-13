variable "environment" {
  type = string
  validation {
    condition     = contains(["test", "production"], var.environment)
    error_message = "environment must be test or production."
  }
}

variable "project_id" { type = string }
variable "region" { type = string }
variable "network_name" { type = string }
variable "database_instance_name" { type = string }
variable "database_name" { type = string }
variable "sql_tier" { type = string }
variable "github_repository" { type = string }
variable "github_ref_pattern" { type = string }
variable "enable_access_release_identity" { type = bool }

variable "state_bucket_name" {
  description = "Existing, environment-isolated bucket used for Terraform state. OP-03 grants only prefix-scoped access."
  type        = string

  validation {
    condition     = length(trimspace(var.state_bucket_name)) > 0
    error_message = "state_bucket_name must name the existing environment state bucket."
  }
}

variable "wif_trust" {
  type = map(object({
    github_environment = string
    workflow_refs      = set(string)
    workflow_claims    = set(string)
    ref_pattern        = string
  }))

  validation {
    condition = length(setsubtract(
      toset(keys(var.wif_trust)),
      toset(["terraform-plan", "terraform-apply", "deploy", "rollback", "admin-bootstrap", "access-release"]),
      )) == 0 && length(setsubtract(
      toset(["terraform-plan", "terraform-apply", "deploy", "rollback", "admin-bootstrap", "access-release"]),
      toset(keys(var.wif_trust)),
    )) == 0
    error_message = "wif_trust must define exactly the six approved workflow identities."
  }

  validation {
    condition     = alltrue([for trust in values(var.wif_trust) : length(trust.workflow_refs) == 1])
    error_message = "Each workflow identity must trust exactly one reviewed workflow ref."
  }

  validation {
    condition     = alltrue([for trust in values(var.wif_trust) : length(trust.workflow_claims) > 0 && length(setsubtract(trust.workflow_claims, toset(["workflow_ref", "job_workflow_ref"]))) == 0])
    error_message = "workflow_claims must contain only workflow_ref and/or job_workflow_ref."
  }

  validation {
    condition = try(
      var.wif_trust["terraform-plan"].workflow_claims == toset(["workflow_ref", "job_workflow_ref"]) &&
      var.wif_trust["terraform-apply"].workflow_claims == toset(["job_workflow_ref"]) &&
      var.wif_trust["deploy"].workflow_claims == toset(["workflow_ref"]) &&
      var.wif_trust["rollback"].workflow_claims == toset(["workflow_ref"]) &&
      var.wif_trust["admin-bootstrap"].workflow_claims == toset(["workflow_ref"]) &&
      var.wif_trust["access-release"].workflow_claims == toset(["workflow_ref"]),
      false,
    )
    error_message = "workflow_claims must match the approved top-level and reusable workflow trust contract."
  }
}

variable "labels" {
  type    = map(string)
  default = {}

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
