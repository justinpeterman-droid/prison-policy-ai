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
