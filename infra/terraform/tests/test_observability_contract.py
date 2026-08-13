import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DASHBOARDS = ROOT / "infra" / "monitoring" / "dashboards"
MODULE = ROOT / "infra" / "terraform" / "modules" / "access_platform"
FORBIDDEN = {
    "field_notes",
    "report_text",
    "employee_number",
    "inmate_identifier",
    "pin",
    "renewal_token",
    "access_token",
}


def test_dashboards_are_valid_and_contain_no_sensitive_fields():
    for filename in ["api.json", "database.json", "jobs-and-ai.json", "client-versions.json"]:
        payload = json.loads((DASHBOARDS / filename).read_text(encoding="utf-8"))
        encoded = json.dumps(payload).lower()
        assert not any(field in encoded for field in FORBIDDEN)
        assert payload["displayName"].startswith("Access ")
        layout = payload["mosaicLayout"]
        assert layout["columns"] == 12
        for tile in layout["tiles"]:
            assert 0 < tile["width"] <= layout["columns"]
            assert tile["height"] > 0
            assert 0 <= tile.get("xPos", 0) < layout["columns"]


def test_every_alert_links_to_a_runbook():
    observability = (MODULE / "observability.tf").read_text(encoding="utf-8")
    assert observability.count("documentation {") >= 10
    assert observability.count("docs/runbooks/") >= 10


def test_backup_workflow_cannot_overwrite_a_fixed_object():
    workflow = (MODULE / "sql_export_workflow.yaml.tftpl").read_text(encoding="utf-8")
    assert "time.format(sys.now()" in workflow
    assert "logical-exports/" in workflow
    assert "offload" in workflow


def test_observability_uses_only_declared_application_producers():
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [MODULE / "observability.tf", *DASHBOARDS.glob("*.json")]
    ).lower()
    assert "request_event" in sources
    assert "ai_provider_repeat_risk_total" in sources
    assert "dependency_health" in sources
    assert "queue_health" in sources
    assert "backup_restore_health" in sources
    assert "client_upgrade_required" in sources
    assert "rp-09" not in sources


def test_telemetry_filters_match_the_exact_emitted_shapes():
    observability = (MODULE / "observability.tf").read_text(encoding="utf-8")
    # ID-02 emits a request_id, not a fabricated event_type. RP-10 emits
    # signal, and RP-07 is a direct custom metric with only job_type.
    assert 'jsonPayload.request_id:*' in observability
    assert 'jsonPayload.signal=\\"dependency_health\\"' in observability
    assert 'jsonPayload.signal=\\"queue_health\\"' in observability
    assert 'jsonPayload.event_type' not in observability
    assert 'metric.label.\\"http_status_class\\"=\\"5xx\\"' in observability
    assert 'metric.type=\\"custom.googleapis.com/ai_provider_repeat_risk_total\\"' in observability


def test_backup_boundary_is_exact_and_workflow_is_bounded():
    backup = (MODULE / "backups.tf").read_text(encoding="utf-8")
    workflow = (MODULE / "sql_export_workflow.yaml.tftpl").read_text(encoding="utf-8")
    services = (MODULE / "project_services.tf").read_text(encoding="utf-8")
    assert 'account_id   = "access-${local.environment_id}-backup"' in backup
    assert "cloudsql.instances.export" in backup and "cloudsql.instances.get" in backup
    assert "cloudsql.operations.get" not in backup
    assert "roles/cloudsql.editor" not in backup
    assert "AccessLogicalBackupExactInstance" in backup
    assert "AccessLogicalBackupExportsOnly" in backup
    assert "objects/logical-exports/" in backup
    assert "roles/workflows.invoker" in backup
    assert "googleapis.sqladmin.v1.operations.get" in workflow
    assert "attempt >= 20" in workflow and "sys.sleep" in workflow
    assert "raise:" in workflow and "timed out" in workflow
    assert '"workflows.googleapis.com"' in services
    assert '"billingbudgets.googleapis.com"' in services
    assert "databases: [${database_name}]" in workflow
    assert "enable_logical_export_scheduler" in backup
    assert "logical_export_polling_authorization_record" in backup
    assert "local.logical_export_scheduler_enabled ? 1 : 0" in backup


def test_all_alerts_have_real_unhealthy_sources_and_never_autoclose():
    observability = (MODULE / "observability.tf").read_text(encoding="utf-8")
    # Budget thresholds are configured by the billing budget resource, not a
    # fabricated monitoring metric. The scanner source is an externally
    # confirmed metric input until its producer is separately provisioned.
    assert "billingbudgets.googleapis.com/budget" not in observability
    assert "var.sensitive_log_scanner_metric_type" in observability
    assert observability.count('alert_strategy { auto_close = "0s" }') >= 11
    assert 'metric.label.\\"http_status_class\\"=\\"5xx\\"' in observability
    assert 'metric.label.\\"result\\"=\\"unavailable\\"' in observability


def test_metric_labels_are_specific_to_actual_producer_shapes():
    observability = (MODULE / "observability.tf").read_text(encoding="utf-8")
    for field in (
        '"client_version"', '"depth_bucket"', '"oldest_age_bucket"',
        '"job_type"', '"stage"', '"recency_bucket"',
        '"parsed_client_version"',
    ):
        assert field in observability
    assert "safe_metric_contracts" in observability


def test_platform_metric_contracts_use_supported_types_only():
    dashboards = "\n".join(path.read_text(encoding="utf-8") for path in DASHBOARDS.glob("*.json"))
    observability = (MODULE / "observability.tf").read_text(encoding="utf-8")
    assert "cloudtasks.googleapis.com/queue/depth" in dashboards
    assert "cloudtasks.googleapis.com/queue/oldest_task_age" not in dashboards
    assert "cloudtasks.googleapis.com/queue/tasks" not in observability
    assert "workflows.googleapis.com/finished_execution_count" in observability
    assert 'metric.label.\\"status\\"=\\"FAILED\\"' in observability
    assert 'resource.type=\\"workflows.googleapis.com/Workflow\\"' in observability
    assert 'resource.label.\\"workflow_id\\"=\\"${google_workflows_workflow.logical_export[0].name}\\"' in observability
    assert 'resource.label.\\"location\\"=\\"${var.region}\\"' in observability
    assert "google_monitoring_uptime_check_config" in observability
    assert 'resource.type=\\"uptime_url\\"' in observability
    assert 'metric.label.\\"check_id\\"=\\"${google_monitoring_uptime_check_config.api_health.uptime_check_id}\\"' in observability
    assert observability.count("depends_on            = [terraform_data.services_ready]") >= 10


def test_billing_spend_is_an_external_bigquery_gate_not_an_invalid_monitoring_metric():
    jobs_dashboard = (DASHBOARDS / "jobs-and-ai.json").read_text(encoding="utf-8")
    assert "billing.googleapis.com/billing/account/cost" not in jobs_dashboard
    assert "Cloud Billing spend source gate" in jobs_dashboard
    assert "BigQuery" in jobs_dashboard
    assert "EXT-04" in jobs_dashboard
