locals {
  storage_buckets = {
    release        = "access-${var.environment}-release"
    configuration  = "access-${var.environment}-configuration"
    logical_backup = "access-${var.environment}-logical-backup"
    roster         = "access-${var.environment}-roster"
    review         = "access-${var.environment}-review"
  }
}

resource "google_storage_bucket" "private" {
  for_each                    = local.storage_buckets
  name                        = each.value
  project                     = var.project_id
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  labels                      = merge(var.labels, { environment = var.environment, purpose = each.key })

  versioning { enabled = true }

  lifecycle_rule {
    action { type = "Delete" }
    condition {
      age                = 90
      num_newer_versions = 2
      with_state         = "ARCHIVED"
    }
  }
  depends_on = [terraform_data.services_ready]
}

resource "google_storage_bucket_iam_member" "release_api_read" {
  bucket = google_storage_bucket.private["release"].name
  role   = "roles/storage.objectViewer"
  member = google_service_account.identities["api"].member
}

resource "google_storage_bucket_iam_member" "bootstrap_request_read" {
  bucket = google_storage_bucket.private["configuration"].name
  role   = "roles/storage.objectViewer"
  member = google_service_account.identities["bootstrap"].member

  condition {
    title       = "ReadAdminBootstrapRequestsOnly"
    description = "Read only opaque first-admin bootstrap request objects."
    expression  = "resource.name.startsWith(\"projects/_/buckets/${google_storage_bucket.private["configuration"].name}/objects/admin-bootstrap-requests/\")"
  }
}

resource "google_storage_bucket_iam_member" "roster_migration_read" {
  bucket = google_storage_bucket.private["roster"].name
  role   = "roles/storage.objectViewer"
  member = google_service_account.identities["migration"].member
}

resource "google_storage_bucket_iam_member" "review_api_read" {
  bucket = google_storage_bucket.private["review"].name
  role   = "roles/storage.objectViewer"
  member = google_service_account.identities["api"].member
}

resource "google_storage_bucket_iam_member" "release_access_release_write" {
  count  = var.enable_access_release_identity ? 1 : 0
  bucket = google_storage_bucket.private["release"].name
  role   = "roles/storage.objectCreator"
  member = google_service_account.identities["access_release"].member

  condition {
    title       = "WriteImmutableReleaseObjects"
    description = "Write only immutable release objects."
    expression  = "resource.name.startsWith(\"projects/_/buckets/${google_storage_bucket.private["release"].name}/objects/releases/\")"
  }
}
