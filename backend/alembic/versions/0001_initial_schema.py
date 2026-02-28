"""Initial schema – runs the full db.sql idempotently.

Revision ID: 0001
Revises: 
Create Date: 2026-02-28

Strategy: execute the complete db.sql via op.execute().
Every DDL statement uses IF NOT EXISTS / OR REPLACE so it
is safe to run against a Supabase DB that already has the
schema partially applied.
"""
from __future__ import annotations

from pathlib import Path

from alembic import op

# revision identifiers
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Path to the canonical SQL schema relative to this file's location
_SQL_FILE = Path(__file__).parent.parent.parent / "docs" / "db.sql"


def upgrade() -> None:
    """Apply the full schema from docs/db.sql (idempotent IF NOT EXISTS)."""
    if not _SQL_FILE.exists():
        raise FileNotFoundError(f"Schema file not found: {_SQL_FILE}")

    sql_content = _SQL_FILE.read_text(encoding="utf-8")

    # Execute each statement in the file.
    # Note: BEGIN/COMMIT in the SQL are handled by Alembic's transaction.
    # Strip them to avoid nested transaction errors.
    cleaned = "\n".join(
        line for line in sql_content.splitlines()
        if line.strip().upper() not in ("BEGIN;", "COMMIT;", "BEGIN", "COMMIT")
    )
    op.execute(cleaned)


def downgrade() -> None:
    """
    Intentionally a no-op – we do not drop production tables via migration.
    Manual teardown required.
    """
    pass
