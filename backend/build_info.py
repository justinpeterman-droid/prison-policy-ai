"""Safe, source-controlled build identifiers for operational API responses.

Values are deliberately identifiers only: callers never receive deployment
configuration, credentials, hosts, or package locations through this module.
"""

import os


SOURCE_COMMIT = os.getenv("SOURCE_COMMIT", "development")
K_REVISION = os.getenv("K_REVISION", "development")
# RP-06's current database head.  A later migration must update this constant
# in the task that owns that migration, rather than querying a live database.
ALEMBIC_REVISION = "20260812_0005"


def build_metadata() -> dict[str, str]:
    """Return the bounded identifiers suitable for logs or safe diagnostics."""
    return {
        "source_commit": SOURCE_COMMIT,
        "cloud_run_revision": K_REVISION,
        "alembic_revision": ALEMBIC_REVISION,
    }
