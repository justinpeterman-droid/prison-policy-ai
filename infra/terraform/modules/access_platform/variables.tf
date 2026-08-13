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
}
