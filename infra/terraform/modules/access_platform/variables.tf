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
}
