resource "google_cloud_run_v2_job" "migration" {
  name     = "access-${var.environment}-migrate"
  project  = var.project_id
  location = var.region
  labels   = local.cloud_run_labels
  template {
    template {
      service_account = google_service_account.identities["migration"].email
      max_retries     = 0
      timeout         = "900s"
      containers {
        image   = var.image_digest
        command = ["python"]
        args    = ["-m", "backend.jobs.migration", "upgrade"]
        resources {
          limits = { cpu = "1", memory = "1Gi" }
        }
        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.containers["access-database-url"].secret_id
              version = "latest"
            }
          }
        }
      }
      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [google_sql_database_instance.postgres.connection_name]
        }
      }
    }
  }
}

resource "google_cloud_run_v2_job" "roster_import" {
  name     = "access-${var.environment}-roster-import"
  project  = var.project_id
  location = var.region
  labels   = local.cloud_run_labels
  template {
    template {
      service_account = google_service_account.identities["migration"].email
      max_retries     = 0
      timeout         = "900s"
      containers {
        image   = var.image_digest
        command = ["python"]
        args    = ["-m", "backend.jobs.roster_import", "--source-uri", var.roster_source_uri, "--corrections-uri", var.roster_corrections_uri, "--report-uri", var.roster_report_uri, "--expected-sha256", var.roster_expected_sha256]
        resources {
          limits = { cpu = "1", memory = "1Gi" }
        }
        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.containers["access-database-url"].secret_id
              version = "latest"
            }
          }
        }
      }
      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [google_sql_database_instance.postgres.connection_name]
        }
      }
    }
  }
}

resource "google_cloud_run_v2_job" "bootstrap_admin" {
  name     = "access-${var.environment}-bootstrap-admin"
  project  = var.project_id
  location = var.region
  labels   = local.cloud_run_labels
  template {
    template {
      service_account = google_service_account.identities["bootstrap"].email
      max_retries     = 0
      timeout         = "900s"
      containers {
        image   = var.image_digest
        command = ["python"]
        args    = ["-m", "backend.jobs.admin_bootstrap", "--request-uri", var.bootstrap_request_uri, "--expected-sha256", var.bootstrap_request_sha256]
        resources {
          limits = { cpu = "1", memory = "1Gi" }
        }
        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.containers["access-database-url"].secret_id
              version = "latest"
            }
          }
        }
      }
      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [google_sql_database_instance.postgres.connection_name]
        }
      }
    }
  }
}

resource "google_cloud_run_v2_job_iam_member" "bootstrap_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.bootstrap_admin.name
  role     = "roles/run.invoker"
  member   = google_service_account.identities["admin_bootstrap"].member
}
