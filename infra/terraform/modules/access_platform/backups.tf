resource "google_service_account" "logical_backup" {
  project = var.project_id
  # `production` cannot appear verbatim in a Google service-account ID: its
  # physical identifier must remain at most 30 characters. Outputs retain the
  # stable logical-backup name.
  account_id   = "access-${local.environment_id}-backup"
  display_name = "Access logical backup"
  depends_on   = [terraform_data.services_ready]
}

resource "google_storage_bucket_iam_member" "logical_backup_creator" {
  bucket = google_storage_bucket.private["logical_backup"].name
  role   = "roles/storage.objectCreator"
  member = google_service_account.logical_backup.member
  condition {
    title       = "AccessLogicalBackupExportsOnly"
    description = "Create only unique logical export objects; no read, overwrite, or delete permission is granted."
    expression  = "resource.name.startsWith(\"projects/_/buckets/${google_storage_bucket.private["logical_backup"].name}/objects/logical-exports/\")"
  }
  depends_on = [terraform_data.services_ready]
}

# Cloud SQL's managed instance identity writes the offloaded object; it can
# create only new logical-export objects in this exact private bucket.
resource "google_storage_bucket_iam_member" "sql_export_writer" {
  bucket = google_storage_bucket.private["logical_backup"].name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${var.sql_export_service_account_email}"

  condition {
    title       = "AccessLogicalExportsOnly"
    description = "Create only unique logical export objects; never read, overwrite, or delete existing objects."
    expression  = "resource.name.startsWith(\"projects/_/buckets/${google_storage_bucket.private["logical_backup"].name}/objects/logical-exports/\")"
  }

  depends_on = [terraform_data.services_ready]
}

resource "google_project_iam_custom_role" "logical_backup_exporter" {
  role_id     = "accessLogicalBackupExport"
  title       = "Access logical backup export"
  description = "Starts Cloud SQL exports for the configured instance; it cannot mutate SQL data or access secrets."
  permissions = ["cloudsql.instances.export", "cloudsql.instances.get"]
}

resource "google_project_iam_member" "logical_backup_exporter" {
  project = var.project_id
  role    = google_project_iam_custom_role.logical_backup_exporter.name
  member  = google_service_account.logical_backup.member

  condition {
    title       = "AccessLogicalBackupExactInstance"
    description = "Permit export operations only for the configured Cloud SQL instance."
    expression  = "resource.name == \"projects/${var.project_id}/instances/${google_sql_database_instance.postgres.name}\""
  }

  depends_on = [terraform_data.services_ready]
}

resource "google_workflows_workflow" "logical_export" {
  project         = var.project_id
  region          = var.region
  name            = "access-${var.environment}-logical-export"
  service_account = google_service_account.logical_backup.email
  source_contents = templatefile("${path.module}/sql_export_workflow.yaml.tftpl", { project_id = var.project_id, instance_name = google_sql_database_instance.postgres.name, database_name = google_sql_database.application.name, bucket_name = google_storage_bucket.private["logical_backup"].name })
  depends_on = [
    terraform_data.services_ready,
    google_project_iam_member.logical_backup_exporter,
    google_storage_bucket_iam_member.logical_backup_creator,
  ]
}

# The scheduler uses the backup identity only to start this exact workflow.
# It receives no project-wide Workflows role or unrelated invoker authority.
resource "google_project_iam_member" "logical_backup_invoker" {
  project = var.project_id
  role    = "roles/workflows.invoker"
  member  = google_service_account.logical_backup.member

  condition {
    title       = "AccessLogicalBackupExactWorkflow"
    description = "Permit invocation only of this environment's logical-export workflow."
    expression  = "resource.name == \"projects/${var.project_id}/locations/${var.region}/workflows/${google_workflows_workflow.logical_export.name}\""
  }

  depends_on = [google_workflows_workflow.logical_export]
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
  depends_on = [
    terraform_data.services_ready,
    google_project_iam_member.logical_backup_invoker,
  ]
}
