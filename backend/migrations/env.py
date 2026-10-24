"""Use API metadata/configuration and allow an explicitly injected test connection."""

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import DatabaseSettings
from app.db import Base
from app.models import User  # noqa: F401 -- register model metadata

target_metadata = Base.metadata


def run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


provided_connection = context.config.attributes.get("connection")
if provided_connection is not None:
    run_migrations(provided_connection)
else:
    database_url = DatabaseSettings().database_url.get_secret_value()
    if context.is_offline_mode():
        context.configure(
            url=database_url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
        with context.begin_transaction():
            context.run_migrations()
    else:
        engine = create_engine(database_url, poolclass=pool.NullPool)
        try:
            with engine.connect() as connection:
                run_migrations(connection)
        finally:
            engine.dispose()
