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
    assert "cloudsql.instances.export" in backup and "cloudsql.operations.get" in backup
    assert "roles/cloudsql.editor" not in backup
    assert "AccessLogicalBackupExactInstance" in backup
    assert "roles/workflows.invoker" in backup
    assert "googleapis.sqladmin.v1.operations.get" in workflow
    assert "attempt >= 20" in workflow and "sys.sleep" in workflow
    assert '"workflows.googleapis.com"' in services
    assert '"billingbudgets.googleapis.com"' in services
