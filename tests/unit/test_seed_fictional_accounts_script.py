from urllib.parse import urlsplit

import pytest

from scripts.seed_fictional_accounts import is_safe_local_database_url


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
