locals {
  dashboard_files = ["api", "database", "jobs-and-ai", "client-versions"]

  # Each key is an independently triaged alert family. Filters reference only
  # the locked application producer contract or platform-native metrics.
  required_alert_filters = {
    auth_lockouts         = "metric.type=\"logging.googleapis.com/user/access_request_event\" AND metric.label.\"error_code\"=\"account_locked\""
    sql_connections       = "metric.type=\"cloudsql.googleapis.com/database/postgresql/num_backends\""
    sql_backup            = "metric.type=\"logging.googleapis.com/user/access_backup_restore_health\""
    ai_job_failure        = "metric.type=\"custom.googleapis.com/ai_provider_repeat_risk_total\""
    ai_job_latency        = "metric.type=\"logging.googleapis.com/user/access_queue_health\""
    policy_search         = "metric.type=\"logging.googleapis.com/user/access_dependency_health\""
    sensitive_log_scanner = "metric.type=\"logging.googleapis.com/user/access_dependency_health\""
    budget                = "metric.type=\"billingbudgets.googleapis.com/budget\""
  }
}

locals {
  # These filters match the exact serialized keys emitted by ID-02 and RP-10.
  # There is intentionally no invented `event_type` key.
  safe_event_filters = {
    request_event           = <<-EOT
      jsonPayload.request_id:* AND jsonPayload.action:* AND jsonPayload.result:* AND jsonPayload.latency_bucket:* AND jsonPayload.http_status_class:* AND jsonPayload.client_version:* AND jsonPayload.dependency:*
    EOT
    dependency_health       = "jsonPayload.signal=\"dependency_health\""
    queue_health            = "jsonPayload.signal=\"queue_health\""
    backup_restore_health   = "jsonPayload.signal=\"backup_restore_health\""
    client_upgrade_required = "jsonPayload.signal=\"client_upgrade_required\""
  }
}

resource "google_monitoring_alert_policy" "required" {
  for_each              = local.required_alert_filters
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
      filter          = each.value
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "60s"
    }
  }
  depends_on = [terraform_data.services_ready]
}
# Each explicit alert below owns its documentation rather than relying on a
# shared generated block.
resource "google_monitoring_alert_policy" "api_availability_documented" {
  project               = var.project_id
  display_name          = "Access API availability documentation"
  combiner              = "OR"
  notification_channels = tolist(var.notification_channel_ids)
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
  conditions {
    display_name = "threshold"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_count\""
      comparison      = "COMPARISON_LT"
      threshold_value = 1
      duration        = "300s"
    }
  }
}
resource "google_monitoring_alert_policy" "api_latency_documented" {
  project               = var.project_id
  display_name          = "Access API latency documentation"
  combiner              = "OR"
  notification_channels = tolist(var.notification_channel_ids)
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
  conditions {
    display_name = "threshold"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_latencies\""
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
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
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
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
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
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
  conditions {
    display_name = "threshold"
    condition_threshold {
      filter          = "metric.type=\"cloudsql.googleapis.com/database/cpu/utilization\""
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
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
  conditions {
    display_name = "threshold"
    condition_threshold {
      filter          = "metric.type=\"cloudsql.googleapis.com/database/disk/utilization\""
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
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
  conditions {
    display_name = "threshold"
    condition_threshold {
      filter          = "metric.type=\"cloudtasks.googleapis.com/queue/tasks\""
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
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
  conditions {
    display_name = "threshold"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/access_queue_health\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "60s"
    }
  }
}
resource "google_monitoring_alert_policy" "logical_export_documented" {
  project               = var.project_id
  display_name          = "Access logical export documentation"
  combiner              = "OR"
  notification_channels = tolist(var.notification_channel_ids)
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
  conditions {
    display_name = "threshold"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/access_backup_restore_health\""
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
  documentation {
    content   = "Owner role: ${var.observability_owner_role}. Runbook: docs/runbooks/backup-restore-disaster-recovery.md"
    mime_type = "text/markdown"
  }
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
  for_each       = toset(local.dashboard_files)
  project        = var.project_id
  dashboard_json = file("${path.module}/../../../monitoring/dashboards/${each.value}.json")
  depends_on     = [terraform_data.services_ready]
}

resource "google_logging_metric" "safe_events" {
  for_each = local.safe_event_filters
  project  = var.project_id
  name     = "access_${each.key}"
  filter   = replace(each.value, "\n", " ")

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"

    labels {
      key         = "action"
      value_type  = "STRING"
      description = "Bounded stable action category from the locked event contract."
    }
    labels {
      key         = "latency_bucket"
      value_type  = "STRING"
      description = "Bounded latency bucket where emitted by the producer."
    }
    labels {
      key         = "http_status_class"
      value_type  = "STRING"
      description = "Bounded HTTP status class emitted by request_event only."
    }
    labels {
      key         = "result"
      value_type  = "STRING"
      description = "Bounded stable result category from the locked event contract."
    }
    labels {
      key         = "error_code"
      value_type  = "STRING"
      description = "Bounded stable error code from the locked event contract."
    }
    labels {
      key         = "dependency"
      value_type  = "STRING"
      description = "Bounded dependency name from the locked event contract."
    }
  }

  label_extractors = {
    action            = "REGEXP_EXTRACT(jsonPayload.action, \"([a-z0-9_]{1,64})\")"
    result            = "REGEXP_EXTRACT(jsonPayload.result, \"([a-z0-9_]{1,64})\")"
    error_code        = "REGEXP_EXTRACT(jsonPayload.error_code, \"([a-z0-9_]{1,64})\")"
    dependency        = "REGEXP_EXTRACT(jsonPayload.dependency, \"([a-z0-9_]{1,64})\")"
    latency_bucket    = "REGEXP_EXTRACT(jsonPayload.latency_bucket, \"([a-z0-9_]{1,64})\")"
    http_status_class = "REGEXP_EXTRACT(jsonPayload.http_status_class, \"([1-5]xx)\")"
  }
  depends_on = [terraform_data.services_ready]
}
