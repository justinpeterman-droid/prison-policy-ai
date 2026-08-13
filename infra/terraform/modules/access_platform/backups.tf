resource "google_service_account" "logical_backup" {
  project      = var.project_id
  account_id   = "access-${var.environment}-logical-backup"
  display_name = "Access logical backup"
  depends_on   = [terraform_data.services_ready]
}

resource "google_storage_bucket_iam_member" "logical_backup_creator" {
  bucket = google_storage_bucket.private["logical_backup"].name
  role   = "roles/storage.objectCreator"
  member = google_service_account.logical_backup.member
}

resource "google_project_iam_custom_role" "logical_backup_exporter" {
  role_id     = "accessLogicalBackupExport"
  title       = "Access logical backup export"
  description = "Starts Cloud SQL exports and reads their operation status; it cannot mutate SQL data or access secrets."
  permissions = ["cloudsql.instances.export", "cloudsql.operations.get"]
}

resource "google_project_iam_member" "logical_backup_exporter" {
  project = var.project_id
  role    = google_project_iam_custom_role.logical_backup_exporter.name
  member  = google_service_account.logical_backup.member
}

resource "google_workflows_workflow" "logical_export" {
  project         = var.project_id
  region          = var.region
  name            = "access-${var.environment}-logical-export"
  service_account = google_service_account.logical_backup.email
  source_contents = templatefile("${path.module}/sql_export_workflow.yaml.tftpl", { project_id = var.project_id, instance_name = google_sql_database_instance.postgres.name, bucket_name = google_storage_bucket.private["logical_backup"].name })
  depends_on = [
    google_project_iam_member.logical_backup_exporter,
    google_storage_bucket_iam_member.logical_backup_creator,
  ]
}

resource "google_cloud_scheduler_job" "logical_export_nightly" {
  project   = var.project_id
  region    = var.region
  name      = "access-${var.environment}-logical-export-nightly"
  schedule  = "0 2 * * *"
  time_zone = "Etc/UTC"
  http_target {
    http_method = "POST"
    uri         = "https://workflowexecutions.googleapis.com/v1/${google_workflows_workflow.logical_export.id}/executions"
    oauth_token {
      service_account_email = google_service_account.logical_backup.email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }
}
