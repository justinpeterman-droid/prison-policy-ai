"""Unit tests for the resolved Agent Builder search config (RC-2).

Pure config assembly — no GCP, no network. These guard the resource path that,
when wrong, 404s every policy search and takes the whole chat down.
"""
import importlib

import pytest

import backend.pipeline.config as config


def _reload(monkeypatch, **env):
    """Reload config with the given env vars applied."""
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return importlib.reload(config)


@pytest.fixture(autouse=True)
def _restore_config():
    """Always leave the module back at its default-env state for other tests."""
    yield
    importlib.reload(config)


class TestServingConfigPath:
    def test_defaults(self):
        path = config.serving_config_path()
        assert path.startswith(f"projects/{config.PROJECT_ID}/locations/global/")
        assert "/collections/default_collection/" in path
        assert "/engines/prison-policies-engine/" in path
        assert path.endswith("/servingConfigs/default_search")

    def test_every_component_is_overridable(self, monkeypatch):
        cfg = _reload(
            monkeypatch,
            GCP_PROJECT_ID="proj-x",
            AGENT_BUILDER_LOCATION="us",
            AGENT_BUILDER_COLLECTION="coll-x",
            AGENT_BUILDER_ENGINE_ID="engine-x",
            AGENT_BUILDER_SERVING_CONFIG="serving-x",
        )
        assert cfg.serving_config_path() == (
            "projects/proj-x/locations/us"
            "/collections/coll-x/engines/engine-x"
            "/servingConfigs/serving-x"
        )

    def test_location_override_alone(self, monkeypatch):
        # The single most likely misconfiguration: an engine created in 'us'
        # while the app still asks 'global'.
        cfg = _reload(monkeypatch, AGENT_BUILDER_LOCATION="us")
        assert "/locations/us/" in cfg.serving_config_path()


class TestSearchConfigSummary:
    def test_reports_resolved_values(self):
        summary = config.search_config_summary()
        assert summary["serving_config_path"] == config.serving_config_path()
        assert summary["engine_id"] == config.AGENT_BUILDER_ENGINE_ID
        assert summary["fast_model"] == config.FAST_MODEL
        assert summary["pro_model"] == config.PRO_MODEL

    def test_carries_no_secrets(self):
        # It gets logged and printed by the diagnostic script, so it must stay
        # free of anything credential-shaped.
        blob = " ".join(str(v).lower() for v in config.search_config_summary().values())
        for banned in ("token", "secret", "password", "bearer", "key"):
            assert banned not in blob
