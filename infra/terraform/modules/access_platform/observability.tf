locals {
  dashboard_files = ["api", "database", "jobs-and-ai", "client-versions"]

  # Each key is an independently triaged alert family. Filters reference only
  # the locked application producer contract or platform-native metrics.
  required_alerts = {
    auth_lockouts           = { filter = "metric.type=\"logging.googleapis.com/user/access_request_event\" AND metric.label.\"error_code\"=\"account_locked\"", comparison = "COMPARISON_GT", threshold = 3, duration = "300s" }
    sql_connections         = { filter = "metric.type=\"cloudsql.googleapis.com/database/postgresql/num_backends\" AND resource.type=\"cloudsql_database\" AND resource.label.\"database_id\"=\"${var.project_id}:${google_sql_database_instance.postgres.name}\"", comparison = "COMPARISON_GT", threshold = 80, duration = "300s" }
    sql_backup              = { filter = "metric.type=\"logging.googleapis.com/user/access_backup_restore_health\" AND metric.label.\"result\"=\"unavailable\"", comparison = "COMPARISON_GT", threshold = 0, duration = "300s" }
    ai_provider_repeat_risk = { filter = "metric.type=\"custom.googleapis.com/ai_provider_repeat_risk_total\"", comparison = "COMPARISON_GT", threshold = 0, duration = "60s" }
    ai_job_failure          = { filter = "metric.type=\"logging.googleapis.com/user/access_queue_health\" AND metric.label.\"result\"=\"failed\" AND metric.label.\"stage\"=\"failed\" AND metric.label.\"job_type\"=~\"^(classify|extract|generate|disciplinary)$\"", comparison = "COMPARISON_GT", threshold = 0, duration = "300s" }
    ai_job_latency          = { filter = "metric.type=\"logging.googleapis.com/user/access_queue_health\" AND metric.label.\"result\"=\"failed\" AND metric.label.\"stage\"=\"failed\" AND metric.label.\"job_type\"=~\"^(classify|extract|generate|disciplinary)$\" AND metric.label.\"latency_bucket\"=~\"^(1m_to_5m|5m_or_more)$\"", comparison = "COMPARISON_GT", threshold = 0, duration = "300s" }
    policy_search           = { filter = "metric.type=\"logging.googleapis.com/user/access_dependency_health\" AND metric.label.\"dependency\"=\"policy_search\" AND metric.label.\"result\"=\"unavailable\"", comparison = "COMPARISON_GT", threshold = 0, duration = "300s" }
    sensitive_log_scanner   = { filter = "metric.type=\"${var.sensitive_log_scanner_metric_type}\"", comparison = "COMPARISON_GT", threshold = 0, duration = "60s" }
  }
}

# A real external health probe distinguishes lack of successful response from
# ordinary traffic volume. It checks only the public /health endpoint.
resource "google_monitoring_uptime_check_config" "api_health" {
  project      = var.project_id
  display_name = "Access ${var.environment} API health"
  timeout      = "10s"
  period       = "60s"

  monitored_resource {
    type = "uptime_url"
    labels = {
      host       = var.managed_hostname
      project_id = var.project_id
    }
  }

  http_check {
    path           = "/health"
    port           = 443
    use_ssl        = true
    request_method = "GET"
  }

  depends_on = [terraform_data.services_ready]
}

locals {
  # Metrics have producer-specific labels; a request metric never invents
  # queue/backup labels and an RP-10 metric never promotes request correlation.
  safe_metric_contracts = {
    request_event           = { filter = local.safe_event_filters.request_event, labels = toset(["action", "result", "latency_bucket", "http_status_class", "error_code", "client_version", "dependency"]) }
    dependency_health       = { filter = local.safe_event_filters.dependency_health, labels = toset(["result", "dependency", "latency_bucket"]) }
    queue_health            = { filter = local.safe_event_filters.queue_health, labels = toset(["result", "depth_bucket", "oldest_age_bucket", "job_type", "stage", "latency_bucket"]) }
    backup_restore_health   = { filter = local.safe_event_filters.backup_restore_health, labels = toset(["result", "recency_bucket"]) }
    client_upgrade_required = { filter = local.safe_event_filters.client_upgrade_required, labels = toset(["result", "parsed_client_version"]) }
  }
}

locals {
  # These filters match the exact serialized keys emitted by ID-02 and RP-10.
  # There is intentionally no invented `event_type` key.
  safe_event_filters = {
    request_event           = <<-EOT
      resource.type="cloud_run_revision" AND resource.labels.service_name="${google_cloud_run_v2_service.api.name}" AND resource.labels.location="${var.region}" AND jsonPayload.request_id:* AND jsonPayload.action:* AND jsonPayload.result:* AND jsonPayload.latency_bucket:* AND jsonPayload.http_status_class:* AND jsonPayload.client_version:* AND jsonPayload.dependency:*
    EOT
    dependency_health       = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${google_cloud_run_v2_service.api.name}\" AND resource.labels.location=\"${var.region}\" AND jsonPayload.signal=\"dependency_health\""
    queue_health            = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${google_cloud_run_v2_service.api.name}\" AND resource.labels.location=\"${var.region}\" AND jsonPayload.signal=\"queue_health\""
    backup_restore_health   = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${google_cloud_run_v2_service.api.name}\" AND resource.labels.location=\"${var.region}\" AND jsonPayload.signal=\"backup_restore_health\""
    client_upgrade_required = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${google_cloud_run_v2_service.api.name}\" AND resource.labels.location=\"${var.region}\" AND jsonPayload.signal=\"client_upgrade_required\""
  }
}

resource "google_monitoring_alert_policy" "required" {
  for_each              = local.required_alerts
  project               = var.project_id
  display_name          = "Access ${replace(each.key, "_", " ")}"
  combiner              = "OR"
  notification_channels = tolist(var.notification_channel_ids)

  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }

  conditions {
    display_name = replace(each.key, "_", " ")
    condition_threshold {
      filter          = each.value.filter
      comparison      = each.value.comparison
      threshold_value = each.value.threshold
      duration        = each.value.duration
    }
  }
  alert_strategy { auto_close = "0s" }
  depends_on = [terraform_data.services_ready]
}
# Each explicit alert below owns its documentation rather than relying on a
# shared generated block.
resource "google_monitoring_alert_policy" "api_availability_documented" {
  project               = var.project_id
  display_name          = "Access API availability documentation"
  combiner              = "OR"
  notification_channels = tolist(var.notification_channel_ids)
  depends_on            = [terraform_data.services_ready]
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
  conditions {
    display_name = "threshold"
    condition_threshold {
      filter          = "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.type=\"uptime_url\" AND metric.label.\"check_id\"=\"${google_monitoring_uptime_check_config.api_health.uptime_check_id}\""
      comparison      = "COMPARISON_LT"
      threshold_value = 1
      duration        = "300s"
    }
  }
  alert_strategy { auto_close = "0s" }
}
resource "google_monitoring_alert_policy" "api_latency_documented" {
  project               = var.project_id
  display_name          = "Access API latency documentation"
  combiner              = "OR"
  notification_channels = tolist(var.notification_channel_ids)
  depends_on            = [terraform_data.services_ready]
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
  alert_strategy { auto_close = "0s" }
  conditions {
    display_name = "threshold"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_latencies\" AND resource.type=\"cloud_run_revision\" AND resource.label.\"service_name\"=\"${google_cloud_run_v2_service.api.name}\" AND resource.label.\"location\"=\"${var.region}\""
      comparison      = "COMPARISON_GT"
      threshold_value = 1000
      duration        = "300s"
    }
  }
}
resource "google_monitoring_alert_policy" "api_5xx_documented" {
  project               = var.project_id
  display_name          = "Access API 5xx documentation"
  combiner              = "OR"
  notification_channels = tolist(var.notification_channel_ids)
  depends_on            = [terraform_data.services_ready]
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
  alert_strategy { auto_close = "0s" }
  conditions {
    display_name = "threshold"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/access_request_event\" AND metric.label.\"http_status_class\"=\"5xx\""
      comparison      = "COMPARISON_GT"
      threshold_value = 5
      duration        = "300s"
    }
  }
}
resource "google_monitoring_alert_policy" "auth_denials_documented" {
  project               = var.project_id
  display_name          = "Access auth denials documentation"
  combiner              = "OR"
  notification_channels = tolist(var.notification_channel_ids)
  depends_on            = [terraform_data.services_ready]
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
  alert_strategy { auto_close = "0s" }
  conditions {
    display_name = "threshold"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/access_request_event\" AND metric.label.\"error_code\"=\"invalid_credentials\""
      comparison      = "COMPARISON_GT"
      threshold_value = 10
      duration        = "300s"
    }
  }
}
resource "google_monitoring_alert_policy" "sql_saturation_documented" {
  project               = var.project_id
  display_name          = "Access SQL saturation documentation"
  combiner              = "OR"
  notification_channels = tolist(var.notification_channel_ids)
  depends_on            = [terraform_data.services_ready]
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
  alert_strategy { auto_close = "0s" }
  conditions {
    display_name = "threshold"
    condition_threshold {
      filter          = "metric.type=\"cloudsql.googleapis.com/database/cpu/utilization\" AND resource.type=\"cloudsql_database\" AND resource.label.\"database_id\"=\"${var.project_id}:${google_sql_database_instance.postgres.name}\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0.85
      duration        = "300s"
    }
  }
}
resource "google_monitoring_alert_policy" "sql_storage_documented" {
  project               = var.project_id
  display_name          = "Access SQL storage documentation"
  combiner              = "OR"
  notification_channels = tolist(var.notification_channel_ids)
  depends_on            = [terraform_data.services_ready]
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
  alert_strategy { auto_close = "0s" }
  conditions {
    display_name = "threshold"
    condition_threshold {
      filter          = "metric.type=\"cloudsql.googleapis.com/database/disk/utilization\" AND resource.type=\"cloudsql_database\" AND resource.label.\"database_id\"=\"${var.project_id}:${google_sql_database_instance.postgres.name}\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8
      duration        = "300s"
    }
  }
}
resource "google_monitoring_alert_policy" "queue_depth_documented" {
  project               = var.project_id
  display_name          = "Access queue depth documentation"
  combiner              = "OR"
  notification_channels = tolist(var.notification_channel_ids)
  depends_on            = [terraform_data.services_ready]
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
  alert_strategy { auto_close = "0s" }
  conditions {
    display_name = "threshold"
    condition_threshold {
      filter          = "metric.type=\"cloudtasks.googleapis.com/queue/depth\" AND resource.type=\"cloudtasks.googleapis.com/Queue\" AND resource.label.\"queue_id\"=\"${google_cloud_tasks_queue.worker.name}\" AND resource.label.\"location\"=\"${var.region}\""
      comparison      = "COMPARISON_GT"
      threshold_value = 1000
      duration        = "300s"
    }
  }
}
resource "google_monitoring_alert_policy" "queue_age_documented" {
  project               = var.project_id
  display_name          = "Access queue age documentation"
  combiner              = "OR"
  notification_channels = tolist(var.notification_channel_ids)
  depends_on            = [terraform_data.services_ready]
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
  alert_strategy { auto_close = "0s" }
  conditions {
    display_name = "threshold"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/access_queue_health\" AND metric.label.\"oldest_age_bucket\"=~\"^(30m_to_2h|2h_or_more)$\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "60s"
    }
  }
}
resource "google_monitoring_alert_policy" "logical_export_documented" {
  count                 = local.logical_export_scheduler_enabled ? 1 : 0
  project               = var.project_id
  display_name          = "Access logical export documentation"
  combiner              = "OR"
  notification_channels = tolist(var.notification_channel_ids)
  depends_on            = [terraform_data.services_ready]
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
  alert_strategy { auto_close = "0s" }
  conditions {
    display_name = "threshold"
    condition_threshold {
      filter          = "metric.type=\"workflows.googleapis.com/finished_execution_count\" AND metric.label.\"status\"=\"FAILED\" AND resource.type=\"workflows.googleapis.com/Workflow\" AND resource.label.\"workflow_id\"=\"${google_workflows_workflow.logical_export[0].name}\" AND resource.label.\"location\"=\"${var.region}\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "60s"
    }
  }
}
resource "google_monitoring_alert_policy" "client_upgrade_documented" {
  project               = var.project_id
  display_name          = "Access client upgrade documentation"
  combiner              = "OR"
  notification_channels = tolist(var.notification_channel_ids)
  depends_on            = [terraform_data.services_ready]
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
  alert_strategy { auto_close = "0s" }
  conditions {
    display_name = "threshold"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/access_client_upgrade_required\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "60s"
    }
  }
}
# Application producers are request_event, ai_provider_repeat_risk_total,
# dependency_health, queue_health, backup_restore_health, and client_upgrade_required.
resource "google_monitoring_dashboard" "access" {
  for_each = toset(local.dashboard_files)
  project  = var.project_id
  dashboard_json = templatefile("${path.module}/../../../monitoring/dashboards/${each.value}.json", {
    project_id          = var.project_id
    region              = var.region
    api_service_name    = google_cloud_run_v2_service.api.name
    worker_service_name = google_cloud_run_v2_service.worker.name
    sql_instance_name   = google_sql_database_instance.postgres.name
    queue_name          = google_cloud_tasks_queue.worker.name
  })
  depends_on = [terraform_data.services_ready]
}

resource "google_logging_metric" "safe_events" {
  for_each = local.safe_metric_contracts
  project  = var.project_id
  name     = "access_${each.key}"
  filter   = replace(each.value.filter, "\n", " ")

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"

    dynamic "labels" {
      for_each = each.value.labels
      content {
        key         = labels.value
        value_type  = "STRING"
        description = "Bounded stable field emitted by this producer."
      }
    }
  }

  label_extractors = { for field in each.value.labels : field => "REGEXP_EXTRACT(jsonPayload.${field}, \"([a-z0-9_.-]{1,64})\")" }
  depends_on       = [terraform_data.services_ready]
}
