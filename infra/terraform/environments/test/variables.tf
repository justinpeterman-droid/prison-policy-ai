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
