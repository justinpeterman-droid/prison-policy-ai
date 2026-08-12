from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TF = ROOT / "infra" / "terraform"


def test_versions_are_exactly_pinned():
    for root in [TF / "bootstrap" / "state", TF / "environments" / "test", TF / "environments" / "production"]:
        versions = (root / "versions.tf").read_text(encoding="utf-8")
        assert 'required_version = "= 1.15.8"' in versions
        assert 'version = "= 7.40.0"' in versions


def test_environment_backends_are_distinct():
    test_backend = (TF / "environments" / "test" / "backend.tf").read_text(encoding="utf-8")
    production_backend = (TF / "environments" / "production" / "backend.tf").read_text(encoding="utf-8")
    assert 'prefix = "access/test"' in test_backend
    assert 'prefix = "access/production"' in production_backend
    assert test_backend != production_backend


def test_lock_files_include_both_runner_platforms():
    for environment in ["test", "production"]:
        lock = (TF / "environments" / environment / ".terraform.lock.hcl").read_text(encoding="utf-8")
        assert 'version     = "7.40.0"' in lock
        assert lock.count('h1:') >= 2
