provider "google" {
  project = var.project_id
  region  = var.region
}

# Remote Terraform state bucket. Created once per environment by a human
# operator; agents never run apply against this root.
resource "google_storage_bucket" "terraform_state" {
  name     = var.state_bucket_name
  project  = var.project_id
  location = var.region

  # State objects are recovered through versioning, never by deleting the
  # bucket out from under a live environment.
  force_destroy               = false
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  logging {
    log_bucket        = var.storage_log_bucket_name
    log_object_prefix = "terraform-state/${var.environment}/"
  }

  # 30-day minimum retention on the live object generation.
  retention_policy {
    retention_period = 2592000
  }

  # Retain superseded state generations for 90 days, then delete them.
  lifecycle_rule {
    action {
      type = "Delete"
    }

    condition {
      days_since_noncurrent_time = 90
      with_state                 = "ARCHIVED"
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

# The only IAM grant on the state bucket. Uniform bucket-level access means
# this binding is the complete access surface for state objects.
resource "google_storage_bucket_iam_member" "state_object_admin" {
  bucket = google_storage_bucket.terraform_state.name
  role   = "roles/storage.objectAdmin"
  member = var.authorized_member
}
