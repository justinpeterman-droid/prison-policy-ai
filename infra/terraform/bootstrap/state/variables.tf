variable "project_id" {
  description = "Google Cloud project that owns the remote-state bucket. Supplied by the human operator at bootstrap time and never committed."
  type        = string

  validation {
    condition     = length(trimspace(var.project_id)) > 0
    error_message = "project_id must be supplied by the operator; it is never committed to the repository."
  }
}

variable "state_bucket_name" {
  description = "Globally unique Cloud Storage bucket that holds Terraform remote state. Supplied by the human operator at bootstrap time and never committed."
  type        = string

  validation {
    condition     = length(trimspace(var.state_bucket_name)) > 0
    error_message = "state_bucket_name must be supplied by the operator; it is never committed to the repository."
  }
}

variable "environment" {
  description = "Environment whose Terraform state is stored in this bucket."
  type        = string
  nullable    = false

  validation {
    condition     = contains(["test", "production"], var.environment)
    error_message = "environment must be test or production."
  }
}

variable "storage_log_bucket_name" {
  description = "Externally provisioned bucket that receives Terraform state bucket access logs."
  type        = string
  nullable    = false

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]$", var.storage_log_bucket_name))
    error_message = "storage_log_bucket_name must be a provider-valid bucket name."
  }
}

variable "region" {
  description = "Regional location of the remote-state bucket."
  type        = string
  default     = "us-central1"
}

variable "authorized_member" {
  description = "The single IAM member granted roles/storage.objectAdmin on the state bucket. Supplied by the human operator and never committed."
  type        = string

  validation {
    condition     = length(trimspace(var.authorized_member)) > 0
    error_message = "authorized_member must be supplied by the operator; it is never committed to the repository."
  }
}
