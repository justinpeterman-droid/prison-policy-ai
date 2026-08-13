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
        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
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
  depends_on = [google_service_account_iam_member.terraform_apply_job_runtime_user]
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
        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
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
  depends_on = [google_service_account_iam_member.terraform_apply_job_runtime_user]
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
        env {
          name  = "ADMIN_BOOTSTRAP_REQUEST_BUCKET"
          value = google_storage_bucket.private["configuration"].name
        }
        env {
          name  = "ADMIN_BOOTSTRAP_REQUEST_PREFIX"
          value = "admin-bootstrap-requests/"
        }
        env {
          name  = "INITIAL_ADMIN_PIN_SECRET"
          value = google_secret_manager_secret.containers["initial-admin-pin"].id
        }
        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
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
  depends_on = [google_service_account_iam_member.terraform_apply_job_runtime_user]
}

resource "google_service_account_iam_member" "terraform_apply_job_runtime_user" {
  for_each = {
    migration = google_service_account.identities["migration"].name
    bootstrap = google_service_account.identities["bootstrap"].name
  }
  service_account_id = each.value
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.identities["terraform_apply"].member
}

resource "google_cloud_run_v2_job_iam_member" "bootstrap_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.bootstrap_admin.name
  role     = "roles/run.invoker"
  member   = google_service_account.identities["admin_bootstrap"].member
}

# Terraform apply provisions job resources and their IAM but cannot execute
# them. The externally bootstrapped apply identity must already be allowed to
# manage this custom role on the first reviewed apply.
resource "google_project_iam_custom_role" "terraform_apply_jobs" {
  project     = var.project_id
  role_id     = "accessOp06JobAdmin"
  title       = "Access OP06 Cloud Run job administration"
  description = "Create and configure the three reviewed jobs without executing them."
  permissions = [
    "run.jobs.create",
    "run.jobs.delete",
    "run.jobs.get",
    "run.jobs.getIamPolicy",
    "run.jobs.list",
    "run.jobs.setIamPolicy",
    "run.jobs.update",
    "run.operations.get",
  ]
}

resource "google_project_iam_member" "terraform_apply_jobs" {
  project = var.project_id
  role    = google_project_iam_custom_role.terraform_apply_jobs.name
  member  = google_service_account.identities["terraform_apply"].member
}

# Deploy may update and execute migration/roster jobs only. Bootstrap remains
# exclusively invokable by the admin-bootstrap workflow identity above.
resource "google_project_iam_custom_role" "deploy_jobs" {
  project     = var.project_id
  role_id     = "accessDeployJobs"
  title       = "Access migration job deployment and invocation"
  description = "Update and invoke only the reviewed migration and roster jobs."
  permissions = [
    "run.jobs.get",
    "run.jobs.run",
    "run.jobs.runWithOverrides",
    "run.jobs.update",
    "run.operations.get",
  ]
}

resource "google_cloud_run_v2_job_iam_member" "deploy_jobs" {
  for_each = {
    migration = google_cloud_run_v2_job.migration.name
    roster    = google_cloud_run_v2_job.roster_import.name
  }
  project  = var.project_id
  location = var.region
  name     = each.value
  role     = google_project_iam_custom_role.deploy_jobs.name
  member   = google_service_account.identities["deploy"].member
}

resource "google_storage_bucket_iam_member" "roster_report_writer" {
  bucket = google_storage_bucket.private["roster"].name
  role   = "roles/storage.objectCreator"
  member = google_service_account.identities["migration"].member

  condition {
    title       = "WriteApprovedRosterReportOnly"
    description = "Create only the operator-approved validation report object."
    expression  = "resource.name == \"projects/_/buckets/${google_storage_bucket.private["roster"].name}/objects/${trimprefix(var.roster_report_uri, "gs://${google_storage_bucket.private["roster"].name}/")}\""
  }
}
