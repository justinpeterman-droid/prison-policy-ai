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
  description = "Dedicated test Terraform state bucket supplied at plan time."
  type        = string

  validation {
    condition     = length(trimspace(var.state_bucket_name)) > 0
    error_message = "state_bucket_name must be supplied at plan time."
  }
}

variable "network_name" {
  description = "Test custom VPC name."
  type        = string
  default     = "access-test"
}

variable "database_instance_name" {
  description = "Test private Cloud SQL instance name."
  type        = string
  default     = "access-test-postgres"
}

variable "database_name" {
  description = "Test application database name."
  type        = string
  default     = "access"
}

variable "sql_tier" {
  description = "Externally reviewed test Cloud SQL machine tier."
  type        = string

  validation {
    condition     = length(trimspace(var.sql_tier)) > 0
    error_message = "sql_tier must be supplied from the reviewed capacity decision."
  }
}

variable "github_ref_pattern" {
  description = "Exact protected Git ref trusted by test workflows."
  type        = string
  default     = "refs/heads/main"

  validation {
    condition     = var.github_ref_pattern == "refs/heads/main"
    error_message = "Test credentialed workflows trust refs/heads/main only."
  }
}

variable "labels" {
  description = "Labels applied to resources created by this root."
  type        = map(string)
  default     = {}
}
