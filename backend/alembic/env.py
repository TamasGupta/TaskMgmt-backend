from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Ensure 'app' package is importable
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings  # noqa: E402
from app.core.database import Base  # noqa: E402
import app.models  # noqa: F401, E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Use psycopg2 (sync) + the pooler URL for Alembic DDL.
# The asyncpg direct-connect port (5432) may be firewalled.
# Pooler port (6543) is always open. psycopg2 works with pooler in any mode.
# We swap the asyncpg driver for psycopg2 in the URL.
# ---------------------------------------------------------------------------
_SYNC_URL = (
    settings.DATABASE_URL
    .replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    # Remove asyncpg-specific query params that psycopg2 doesn't understand
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=_SYNC_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import create_engine  # noqa: PLC0415

    connectable = create_engine(
        _SYNC_URL,
        poolclass=pool.NullPool,  # no connection pool for migrations
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_schemas=False,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
