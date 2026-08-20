import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit

import pytest

import scripts.seed_fictional_accounts as seed_module
from scripts.seed_fictional_accounts import is_safe_local_database_url


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "seed_fictional_accounts.py"


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://postgres:postgres@localhost:5432/prison_policy",
        "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/prison_policy",
        "postgresql+psycopg://postgres:postgres@[::1]:5432/prison_policy",
    ],
)
def test_accepts_loopback_postgres_database_urls(url):
    assert is_safe_local_database_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://user:pw@db.example.com/prison_policy",
        "postgresql+psycopg://user:pw@10.0.0.5/prison_policy",
        "postgresqlfake://user:pw@localhost/prison_policy",
        "sqlite:///local.db",
        "",
    ],
)
def test_rejects_nonlocal_or_nonpostgres_database_urls(url):
    assert is_safe_local_database_url(url) is False


def test_url_parser_does_not_treat_hostname_text_as_loopback():
    parsed = urlsplit("postgresql+psycopg://user:pw@localhost.example.com/db")
    assert parsed.hostname == "localhost.example.com"
    assert is_safe_local_database_url(parsed.geturl()) is False


def test_direct_cli_invocation_loads_repo_and_rejects_unsafe_database(tmp_path):
    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite:///unsafe.db"

    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Refusing to seed fictional accounts" in result.stderr
    assert "ModuleNotFoundError" not in result.stderr


def test_success_output_never_logs_fictional_credentials(monkeypatch, capsys):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/prison_policy",
    )
    monkeypatch.setattr(seed_module, "seed_fictional_accounts", lambda _url: None)

    assert seed_module.main() == 0
    captured = capsys.readouterr()

    assert "Seeded standard fictional local accounts." in captured.out
    assert "docs/local-fictional-accounts.md" in captured.out
    for spec in seed_module.FICTIONAL_ACCOUNTS:
        assert spec["employee_number"] not in captured.out
        assert spec["pin"] not in captured.out
