resource "google_artifact_registry_repository" "backend" {
  project       = var.project_id
  location      = var.region
  repository_id = var.image_repository_id
  format        = "DOCKER"
  kms_key_name  = var.artifact_registry_kms_key_name
  depends_on    = [google_project_service.required]
}


locals {
  cloud_run_labels = merge(var.labels, {
    source       = var.source_commit
    release      = substr(replace(lower(var.release_version), "/[^a-z0-9_-]/", "-"), 0, 63)
    image_digest = substr(sha256(var.image_digest), 0, 63)
  })
}

resource "google_cloud_run_v2_service" "api" {
  name     = "access-${var.environment}-api"
  project  = var.project_id
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
  labels   = local.cloud_run_labels

  # Protected delivery workflows own immutable revision images and traffic.
  # Terraform continues to own ingress, identity, scaling, configuration,
  # secrets, IAM, and every other service field.
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      traffic,
    ]
  }

  template {
    service_account                  = google_service_account.api.email
    timeout                          = "300s"
    execution_environment            = "EXECUTION_ENVIRONMENT_GEN2"
    max_instance_request_concurrency = var.api_max_concurrency
    containers {
      image   = var.image_digest
      command = ["gunicorn"]
      args    = ["--bind", ":8080", "--workers", "1", "--threads", "8", "--timeout", "300", "backend.webapp.app:create_app()"]
      resources {
        limits = { cpu = "1", memory = "1Gi" }
      }
      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 0
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 18
      }
      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 0
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 18
      }
      env {
        name  = "ACCESS_API_ENABLED"
        value = "true"
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_LOCATION"
        value = var.region
      }
      env {
        name  = "GCP_MODEL_LOCATION"
        value = var.gcp_model_location
      }
      env {
        name  = "AGENT_BUILDER_LOCATION"
        value = var.agent_builder_location
      }
      env {
        name  = "AGENT_BUILDER_COLLECTION"
        value = var.agent_builder_collection
      }
      env {
        name  = "AGENT_BUILDER_ENGINE_ID"
        value = var.agent_builder_engine_id
      }
      env {
        name  = "AGENT_BUILDER_SERVING_CONFIG"
        value = var.agent_builder_serving_config
      }
      env {
        name  = "FAST_MODEL"
        value = var.fast_model
      }
      env {
        name  = "PRO_MODEL"
        value = var.pro_model
      }
      env {
        name  = "CLOUD_TASKS_PROJECT"
        value = var.project_id
      }
      env {
        name  = "CLOUD_TASKS_LOCATION"
        value = var.region
      }
      env {
        name  = "CLOUD_TASKS_QUEUE"
        value = google_cloud_tasks_queue.worker.name
      }
      env {
        name  = "AI_WORKER_URL"
        value = google_cloud_run_v2_service.worker.uri
      }
      env {
        name  = "CLOUD_TASKS_OIDC_SERVICE_ACCOUNT"
        value = google_service_account.task_invoker.email
      }
      env {
        name  = "SOURCE_COMMIT"
        value = var.source_commit
      }
      env {
        name  = "PUBLIC_BASE_URL"
        value = "https://${var.managed_hostname}"
      }
      env {
        name  = "LEGACY_REPORT_MODE"
        value = var.legacy_report_mode
      }
      env {
        name  = "ROSTER_BUCKET"
        value = google_storage_bucket.private["roster"].name
      }
      env {
        name  = "REVIEW_BUCKET"
        value = google_storage_bucket.private["review"].name
      }
      env {
        name  = "REVIEW_OBJECT_PREFIX"
        value = var.review_object_prefix
      }
      env {
        name  = "LOG_LEVEL"
        value = var.log_level
      }
      env {
        name  = "RELEASE_VERSION"
        value = var.release_version
      }
      env {
        name  = "API_VERSION"
        value = var.api_version
      }
      env {
        name  = "LATEST_CLIENT_VERSION"
        value = var.latest_client_version
      }
      env {
        name  = "MINIMUM_CLIENT_VERSION"
        value = var.minimum_client_version
      }
      env {
        name  = "MINIMUM_SERVER_VERSION"
        value = var.minimum_server_version
      }
      env {
        name  = "RELEASE_NOTES"
        value = var.release_notes
      }
      env {
        name  = "ACCESS_RELEASE_BUCKET"
        value = google_storage_bucket.private["release"].name
      }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.access_database_url.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "IDENTITY_HASH_PEPPER"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.identity_hash_pepper.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "CURSOR_SIGNING_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.cursor_signing_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "CLIENT_UPDATE_GRANT_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.client_update_grant_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "ACCESS_CODE"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.legacy_access_code.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "ADMIN_CODE"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.legacy_admin_code.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "GITHUB_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.github_feedback_token.secret_id
            version = "latest"
          }
        }
      }
      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }
    scaling {
      min_instance_count = var.api_min_instances
      max_instance_count = var.api_max_instances
    }
    volumes {
      name = "cloudsql"
      cloud_sql_instance { instances = [google_sql_database_instance.postgres.connection_name] }
    }
  }
}

resource "google_cloud_run_v2_service" "worker" {
  name     = "access-${var.environment}-worker"
  project  = var.project_id
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  labels   = local.cloud_run_labels

  # Protected delivery workflows select the reviewed worker revision.
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      traffic,
    ]
  }

  template {
    service_account                  = google_service_account.worker.email
    timeout                          = "900s"
    execution_environment            = "EXECUTION_ENVIRONMENT_GEN2"
    max_instance_request_concurrency = var.worker_max_concurrency
    containers {
      image   = var.image_digest
      command = ["gunicorn"]
      args    = ["--bind", ":8080", "--workers", "1", "--threads", "4", "--timeout", "900", "backend.worker.app:create_worker_app()"]
      resources { limits = { cpu = "1", memory = "1Gi" } }
      startup_probe {
        tcp_socket {
          port = 8080
        }
        initial_delay_seconds = 0
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 18
      }
      liveness_probe {
        tcp_socket {
          port = 8080
        }
        initial_delay_seconds = 0
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 18
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_LOCATION"
        value = var.region
      }
      env {
        name  = "GCP_MODEL_LOCATION"
        value = var.gcp_model_location
      }
      env {
        name  = "AGENT_BUILDER_LOCATION"
        value = var.agent_builder_location
      }
      env {
        name  = "AGENT_BUILDER_COLLECTION"
        value = var.agent_builder_collection
      }
      env {
        name  = "AGENT_BUILDER_ENGINE_ID"
        value = var.agent_builder_engine_id
      }
      env {
        name  = "AGENT_BUILDER_SERVING_CONFIG"
        value = var.agent_builder_serving_config
      }
      env {
        name  = "FAST_MODEL"
        value = var.fast_model
      }
      env {
        name  = "PRO_MODEL"
        value = var.pro_model
      }
      env {
        name  = "SOURCE_COMMIT"
        value = var.source_commit
      }
      env {
        name  = "LOG_LEVEL"
        value = var.log_level
      }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.access_database_url.secret_id
            version = "latest"
          }
        }
      }
      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }
    scaling {
      min_instance_count = var.worker_min_instances
      max_instance_count = var.worker_max_instances
    }
    volumes {
      name = "cloudsql"
      cloud_sql_instance { instances = [google_sql_database_instance.postgres.connection_name] }
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "worker_task_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.worker.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.task_invoker.email}"
}

resource "google_cloud_run_v2_service_iam_member" "api_public_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_artifact_registry_repository_iam_member" "deploy_writer" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.backend.name
  role       = "roles/artifactregistry.writer"
  member     = google_service_account.workflow["deploy"].member
}

resource "google_cloud_run_v2_service_iam_member" "deploy_services" {
  for_each = { api = google_cloud_run_v2_service.api.name, worker = google_cloud_run_v2_service.worker.name }
  project  = var.project_id
  location = var.region
  name     = each.value
  role     = google_project_iam_custom_role.deploy_revision.name
  member   = google_service_account.workflow["deploy"].member
}

resource "google_cloud_run_v2_service_iam_member" "rollback_services" {
  for_each = { api = google_cloud_run_v2_service.api.name, worker = google_cloud_run_v2_service.worker.name }
  project  = var.project_id
  location = var.region
  name     = each.value
  role     = google_project_iam_custom_role.rollback_traffic.name
  member   = google_service_account.workflow["rollback"].member
}
