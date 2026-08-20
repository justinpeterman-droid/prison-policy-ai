variable "project_id" {
  description = "Google Cloud project dedicated to the production environment. Supplied at plan time and never committed."
  type        = string

  validation {
    condition     = length(trimspace(var.project_id)) > 0
    error_message = "project_id must be supplied at plan time; it is never committed to the repository."
  }
}

variable "environment" {
  description = "Environment name. This root manages production only."
  type        = string
  default     = "production"

  validation {
    condition     = var.environment == "production"
    error_message = "This root manages the production environment only; environment must be \"production\"."
  }
}

variable "region" {
  description = "Primary region for production regional resources. Locked to us-central1 by approved regional placement."
  type        = string
  default     = "us-central1"

  validation {
    condition     = var.region == "us-central1"
    error_message = "Production regional resources are approved for us-central1 only."
  }
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
  description = "Dedicated production Terraform state bucket supplied at plan time."
  type        = string

  validation {
    condition     = length(trimspace(var.state_bucket_name)) > 0
    error_message = "state_bucket_name must be supplied at plan time."
  }
}

variable "network_name" {
  description = "Production custom VPC name."
  type        = string
  default     = "access-production"
}

variable "database_instance_name" {
  description = "Production private Cloud SQL instance name."
  type        = string
  default     = "access-production-postgres"
}

variable "database_name" {
  description = "Production application database name."
  type        = string
  default     = "access"
}

variable "sql_tier" {
  description = "Externally reviewed production Cloud SQL machine tier."
  type        = string

  validation {
    condition     = length(trimspace(var.sql_tier)) > 0
    error_message = "sql_tier must be supplied from the reviewed capacity decision."
  }
}

variable "github_ref_pattern" {
  description = "Exact protected Git ref trusted by production workflows."
  type        = string
  default     = "refs/heads/main"

  validation {
    condition     = var.github_ref_pattern == "refs/heads/main"
    error_message = "Production credentialed workflows trust refs/heads/main only."
  }
}

variable "labels" {
  description = "Labels applied to resources created by this root."
  type        = map(string)
  default     = {}
}
