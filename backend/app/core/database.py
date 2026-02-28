from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ---------------------------------------------------------------------------
# Engine – service-role connection; bypasses Supabase RLS at DB level.
# All RBAC enforcement happens in Python (services/deps).
#
# PgBouncer (transaction mode) compatibility:
#   asyncpg must NOT use prepared statements.
#
# The ?prepared_statement_cache_size=0 query param on the asyncpg URL
# is the canonical way to disable prepared statements in asyncpg 0.27+.
# This prevents "DuplicatePreparedStatementError" with PgBouncer.
# ---------------------------------------------------------------------------

# Append the prepared_statement_cache_size=0 param if not already present
_db_url = settings.DATABASE_URL
if "prepared_statement_cache_size" not in _db_url:
    _db_url += ("&" if "?" in _db_url else "?") + "prepared_statement_cache_size=0"

engine = create_async_engine(
    _db_url,
    pool_pre_ping=True,
    pool_size=3,
    max_overflow=5,
    echo=settings.APP_ENV == "development",
    json_serializer=json.dumps,
    json_deserializer=json.loads,
)

AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async DB session."""
    async with AsyncSessionFactory() as session:
        yield session
