"""RP-10 build metadata is safe and deterministic in local/test runs."""

import importlib


def test_build_metadata_contains_only_safe_release_identifiers(monkeypatch):
    monkeypatch.setenv("SOURCE_COMMIT", "f" * 40)
    monkeypatch.setenv("K_REVISION", "fictional-cloud-run-revision")
    import backend.build_info as build_info

    build_info = importlib.reload(build_info)
    info = build_info.build_metadata()

    assert info == {
        "source_commit": "f" * 40,
        "cloud_run_revision": "fictional-cloud-run-revision",
        "alembic_revision": build_info.ALEMBIC_REVISION,
    }
    assert all("token" not in name and "secret" not in name for name in info)
