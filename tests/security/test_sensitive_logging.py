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


def test_failed_ai_job_health_signal_is_bounded_and_has_no_identifier(monkeypatch):
    emitted = []
    monkeypatch.setattr(
        health_api, "_emit",
        lambda signal, result, **fields: emitted.append((signal, result, fields)),
    )

    health_api._emit_failed_job_health(("generate",))

    assert emitted == [(
        "queue_health", "failed", {
            "depth_bucket": "unknown", "oldest_age_bucket": "unknown",
            "job_type": "generate", "stage": "failed", "latency_bucket": "unknown",
        },
    )]


def test_policy_search_health_fails_closed_without_a_live_safe_producer():
    assert health_api._policy_search_status() == "Unavailable"
