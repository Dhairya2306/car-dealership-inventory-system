"""Load database configuration without storing credentials in alembic.ini."""

import os
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

from app.db import Base

# Import model modules here when they exist so autogenerate sees their tables.
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
database_url = os.environ["DATABASE_URL"]
target_metadata = Base.metadata

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
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
