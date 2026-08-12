from sqlalchemy import text

from backend.identity.config import IdentitySettings
from backend.persistence import database


def test_postgresql_foundation_uses_utc_and_is_ready(db_engine):
    with db_engine.connect() as connection:
        assert connection.execute(text("SHOW TIME ZONE")).scalar_one() == "UTC"

    settings = IdentitySettings.from_env({
        "ACCESS_API_ENABLED": "true",
        "DATABASE_URL": str(db_engine.url),
        "IDENTITY_HASH_PEPPER": "p" * 32,
        "CURSOR_SIGNING_KEY": "c" * 32,
        "PUBLIC_BASE_URL": "https://review.example.gov",
    })
    database.init_database(settings)
    assert database.database_ready() is True
