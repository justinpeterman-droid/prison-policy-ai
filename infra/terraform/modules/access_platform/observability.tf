locals {
  dashboard_files = ["api", "database", "jobs-and-ai", "client-versions"]

  # Each key is an independently triaged alert family. Filters reference only
  # the locked application producer contract or platform-native metrics.
  required_alert_filters = {
    auth_lockouts         = "metric.type=\"logging.googleapis.com/user/access_request_event\" AND metric.label.\"error_code\"=\"auth_lockout\""
    sql_connections       = "metric.type=\"cloudsql.googleapis.com/database/postgresql/num_backends\""
    sql_backup            = "metric.type=\"logging.googleapis.com/user/access_backup_restore_health\""
    ai_job_failure        = "metric.type=\"logging.googleapis.com/user/access_dependency_health\" AND metric.label.\"dependency\"=\"ai\""
    ai_job_latency        = "metric.type=\"logging.googleapis.com/user/access_request_event\" AND metric.label.\"action\"=\"ai_job\""
    policy_search         = "metric.type=\"logging.googleapis.com/user/access_dependency_health\" AND metric.label.\"dependency\"=\"policy_search\""
    sensitive_log_scanner = "metric.type=\"logging.googleapis.com/user/access_dependency_health\" AND metric.label.\"dependency\"=\"sensitive_log_scanner\""
    budget                = "metric.type=\"billingbudgets.googleapis.com/budget\""
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
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "60s"
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
      threshold_value = 0
      duration        = "60s"
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
      filter          = "metric.type=\"logging.googleapis.com/user/access_request_event\" AND metric.label.\"result\"=\"server_error\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "60s"
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
      filter          = "metric.type=\"logging.googleapis.com/user/access_request_event\" AND metric.label.\"action\"=\"auth\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "60s"
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
      threshold_value = 0
      duration        = "60s"
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
      threshold_value = 0
      duration        = "60s"
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
      threshold_value = 0
      duration        = "60s"
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
}

resource "google_logging_metric" "safe_events" {
  for_each = toset(["request_event", "dependency_health", "queue_health", "backup_restore_health", "client_upgrade_required"])
  project  = var.project_id
  name     = "access_${each.value}"
  filter   = "jsonPayload.event_type=\"${each.value}\""

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
    action     = "REGEXP_EXTRACT(jsonPayload.action, \"([a-z0-9_]{1,64})\")"
    result     = "REGEXP_EXTRACT(jsonPayload.result, \"([a-z0-9_]{1,64})\")"
    error_code = "REGEXP_EXTRACT(jsonPayload.error_code, \"([a-z0-9_]{1,64})\")"
    dependency = "REGEXP_EXTRACT(jsonPayload.dependency, \"([a-z0-9_]{1,64})\")"
  }
}
