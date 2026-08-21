resource "google_cloud_tasks_queue" "worker" {
  name     = "access-${var.environment}-worker"
  project  = var.project_id
  location = var.region

  rate_limits {
    max_concurrent_dispatches = var.queue_max_concurrent_dispatches
    max_dispatches_per_second = var.queue_max_dispatches_per_second
  }
  retry_config {
    max_attempts       = var.queue_max_attempts
    min_backoff        = "5s"
    max_backoff        = "300s"
    max_doublings      = 5
    max_retry_duration = "3600s"
  }
  depends_on = [google_project_service.required]
}

resource "google_cloud_tasks_queue_iam_member" "api_enqueuer" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_tasks_queue.worker.name
  role     = "roles/cloudtasks.enqueuer"
  member   = google_service_account.api.member
}
