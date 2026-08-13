import pytest

from backend.identity.config import IdentitySettings


def test_disabled_identity_does_not_require_database_secrets():
    settings = IdentitySettings.from_env({"ACCESS_API_ENABLED": "false"})
    assert settings.enabled is False
    assert settings.database_url is None


def test_enabled_identity_requires_database_and_hashing_secrets():
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        IdentitySettings.from_env({"ACCESS_API_ENABLED": "true"})


def test_enabled_identity_parses_complete_configuration():
    settings = IdentitySettings.from_env(
        {
            "ACCESS_API_ENABLED": "true",
            "DATABASE_URL": "postgresql+psycopg://app:test@localhost/access_test",
            "IDENTITY_HASH_PEPPER": "p" * 32,
            "CURSOR_SIGNING_KEY": "c" * 32,
            "RELEASE_VERSION": "1.4.0",
            "LATEST_CLIENT_VERSION": "1.4.0",
            "MINIMUM_CLIENT_VERSION": "1.2.0",
            "MINIMUM_SERVER_VERSION": "1.2.0",
            "API_VERSION": "v1",
            "RELEASE_NOTES": "Fictional reviewed release.",
            "PUBLIC_BASE_URL": "https://review.example.gov",
        }
    )
    assert settings.enabled is True
    assert settings.minimum_client_version == "1.2.0"
    assert settings.minimum_server_version == "1.2.0"
    assert settings.api_version == "v1"
    assert settings.review_lab_origin == "https://review.example.gov"
    assert settings.access_ttl_seconds == 900
    assert settings.nonpersistent_renewal_ttl_seconds == 43_200
    assert settings.persistent_renewal_ttl_seconds == 2_592_000


@pytest.mark.parametrize("value", ["1", "version-one", "1.0+local"])
def test_client_versions_must_be_public_semantic_versions(value):
    env = {
        "ACCESS_API_ENABLED": "true",
        "DATABASE_URL": "postgresql+psycopg://app:test@localhost/access_test",
        "IDENTITY_HASH_PEPPER": "p" * 32,
        "CURSOR_SIGNING_KEY": "c" * 32,
        "RELEASE_VERSION": "1.4.0",
        "LATEST_CLIENT_VERSION": value,
        "MINIMUM_CLIENT_VERSION": "1.2.0",
        "PUBLIC_BASE_URL": "https://review.example.gov",
    }
    with pytest.raises(RuntimeError, match="LATEST_CLIENT_VERSION"):
        IdentitySettings.from_env(env)


def test_minimum_client_version_cannot_exceed_latest():
    env = {
        "ACCESS_API_ENABLED": "true",
        "DATABASE_URL": "postgresql+psycopg://app:test@localhost/access_test",
        "IDENTITY_HASH_PEPPER": "p" * 32,
        "CURSOR_SIGNING_KEY": "c" * 32,
        "RELEASE_VERSION": "1.4.0",
        "LATEST_CLIENT_VERSION": "1.4.0",
        "MINIMUM_CLIENT_VERSION": "1.5.0",
        "PUBLIC_BASE_URL": "https://review.example.gov",
    }
    with pytest.raises(RuntimeError, match="MINIMUM_CLIENT_VERSION"):
        IdentitySettings.from_env(env)


@pytest.mark.parametrize("value", ["1", "server-one", "1.0+local"])
def test_minimum_server_version_must_be_public_semantic_version(value):
    env = {
        "ACCESS_API_ENABLED": "true",
        "DATABASE_URL": "postgresql+psycopg://app:test@localhost/access_test",
        "IDENTITY_HASH_PEPPER": "p" * 32,
        "CURSOR_SIGNING_KEY": "c" * 32,
        "RELEASE_VERSION": "1.4.0",
        "LATEST_CLIENT_VERSION": "1.4.0",
        "MINIMUM_CLIENT_VERSION": "1.2.0",
        "MINIMUM_SERVER_VERSION": value,
        "PUBLIC_BASE_URL": "https://review.example.gov",
    }
    with pytest.raises(RuntimeError, match="MINIMUM_SERVER_VERSION"):
        IdentitySettings.from_env(env)


@pytest.mark.parametrize("notes", ["", "line one\nline two", "x" * 501])
def test_release_notes_are_one_safe_bounded_line(notes):
    env = {
        "ACCESS_API_ENABLED": "true",
        "DATABASE_URL": "postgresql+psycopg://app:test@localhost/access_test",
        "IDENTITY_HASH_PEPPER": "p" * 32,
        "CURSOR_SIGNING_KEY": "c" * 32,
        "RELEASE_NOTES": notes,
        "PUBLIC_BASE_URL": "https://review.example.gov",
    }
    with pytest.raises(RuntimeError, match="RELEASE_NOTES"):
        IdentitySettings.from_env(env)


@pytest.mark.parametrize(
    "url",
    [
        "http://review.example.gov",
        "https://review.example.gov/path",
        "https://user:pass@review.example.gov",
        "https://review.example.gov?token=value",
    ],
)
def test_public_base_url_must_be_an_https_origin(url):
    env = {
        "ACCESS_API_ENABLED": "true",
        "DATABASE_URL": "postgresql+psycopg://app:test@localhost/access_test",
        "IDENTITY_HASH_PEPPER": "p" * 32,
        "CURSOR_SIGNING_KEY": "c" * 32,
        "PUBLIC_BASE_URL": url,
    }
    with pytest.raises(RuntimeError, match="PUBLIC_BASE_URL"):
        IdentitySettings.from_env(env)
