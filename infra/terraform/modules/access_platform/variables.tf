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

variable "wif_trust" {
  type = map(object({
    github_environment = string
    workflow_refs      = set(string)
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
}

variable "labels" {
  type    = map(string)
  default = {}
}
