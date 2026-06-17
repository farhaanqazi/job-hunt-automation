"""Schema lifecycle helpers.

v1 uses ``create_schema`` from :mod:`jobhunt.storage.database` to create tables on demand.
This module is a placeholder for future incremental migrations (see plan section 12).
"""

from jobhunt.storage.database import create_schema, get_engine


def init_database(database_url: str) -> None:
    """Create the schema for a fresh database."""
    create_schema(get_engine(database_url))
