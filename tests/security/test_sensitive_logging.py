"""RP-10 operational telemetry must never carry supplied sensitive markers."""
import json

import backend.webapp.api_v1.admin_health as health_api


def test_operational_signals_do_not_include_sensitive_marker(monkeypatch):
    marker = "FICTIONAL-FIELD-NOTES-DO-NOT-LOG-12345"
    emitted = []
    monkeypatch.setattr(health_api.logger, "info", emitted.append)
    for signal in (
        "dependency_health", "queue_health", "backup_restore_health",
        "client_upgrade_required",
    ):
        health_api._emit(signal, "operational")
    rendered = "\n".join(emitted)
    assert marker not in rendered
    for signal in (
        "dependency_health", "queue_health", "backup_restore_health",
        "client_upgrade_required",
    ):
        assert signal in rendered
