variable "project_id" {
  description = "Google Cloud project dedicated to the test environment. Supplied at plan time and never committed."
  type        = string

  validation {
    condition     = length(trimspace(var.project_id)) > 0
    error_message = "project_id must be supplied at plan time; it is never committed to the repository."
  }
}

variable "environment" {
  description = "Environment name. This root manages test only."
  type        = string
  default     = "test"

  validation {
    condition     = var.environment == "test"
    error_message = "This root manages the test environment only; environment must be \"test\"."
  }
}

variable "region" {
  description = "Primary region for test regional resources."
  type        = string
  default     = "us-central1"
}

variable "source_repository" {
  description = "Repository allowed to deploy this environment, used by later tasks to scope workload-identity trust. Supplied at plan time and never committed."
  type        = string

  validation {
    condition     = length(trimspace(var.source_repository)) > 0
    error_message = "source_repository must be supplied at plan time; it is never committed to the repository."
  }
}

variable "state_bucket_name" {
  description = "Existing test Terraform state bucket. Supplied at plan time and never committed."
  type        = string

  validation {
    condition     = length(trimspace(var.state_bucket_name)) > 0
    error_message = "state_bucket_name must be supplied at plan time."
  }
}

variable "labels" {
  description = "Labels applied to resources created by this root."
  type        = map(string)
  default     = {}
}

# These declarations let the shared mocked native test pass production's
# required external inputs without embedding them in production/main.tf.
variable "image_digest" { type = string }
variable "source_commit" { type = string }
variable "release_version" { type = string }
variable "api_version" { type = string }
variable "latest_client_version" { type = string }
variable "minimum_client_version" { type = string }
variable "minimum_server_version" { type = string }
variable "release_notes" { type = string }
variable "managed_hostname" { type = string }
variable "dns_zone_name" { type = string }
variable "image_repository_id" { type = string }
variable "queue_max_attempts" { type = number }
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
variable "notification_channel_ids" { type = set(string) }
variable "billing_account_id" { type = string }
variable "monthly_budget_amount" { type = number }
variable "budget_pubsub_topic" { type = string }
variable "observability_owner_role" { type = string }
variable "sensitive_log_scanner_metric_type" { type = string }
