"""enable required postgres extensions (pgvector, pgcrypto)

Revision ID: 0001_enable_extensions
Revises:
Create Date: 2026-07-21

Baseline migration. Business tables are created by later migrations as each
module lands (Sprint 3+). This one only provisions extensions the schema will
rely on: ``vector`` for RAG embeddings and ``pgcrypto`` for UUID/crypto helpers.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001_enable_extensions"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite (tests) has no extensions; nothing to do.
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
