"""Fail-closed ACCESS_CODE configuration tests."""
import os
import subprocess
import sys

import pytest

from backend.webapp import app as app_mod


def test_config_preserves_missing_access_code_as_none():
    """Removing the fallback must leave omission visible to the app factory."""
    env = os.environ.copy()
    env.pop("ACCESS_CODE", None)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from backend.pipeline.config import ACCESS_CODE; print(repr(ACCESS_CODE))",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "None"


def test_create_app_rejects_missing_access_code(monkeypatch):
    """A web process must never start behind an implicit credential."""
    monkeypatch.setattr(app_mod, "ACCESS_CODE", None)
    with pytest.raises(RuntimeError, match="ACCESS_CODE must be configured"):
        app_mod.create_app()


def test_create_app_allows_explicitly_empty_access_code(monkeypatch):
    """An explicit empty value retains the isolated local-work bypass."""
    monkeypatch.setattr(app_mod, "ACCESS_CODE", "")
    monkeypatch.setattr(app_mod, "ADMIN_CODE", "")
    app = app_mod.create_app()
    assert app.test_client().get("/").status_code == 200


def test_create_app_keeps_configured_access_code_gate(monkeypatch):
    """A configured shared code must continue protecting application pages."""
    monkeypatch.setattr(app_mod, "ACCESS_CODE", "configured-code")
    monkeypatch.setattr(app_mod, "ADMIN_CODE", "")
    app = app_mod.create_app()
    assert app.test_client().get("/").status_code == 302
