"""SQLAlchemy models for clinical. Cross-dialect (Postgres + SQLite for tests).

``output``/``sources`` are stored as ``jsonb`` on Postgres (docs/03 ai_recommendations)
and fall back to generic ``JSON`` on SQLite so the integration harness can create the
schema in-memory.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import JSON, Boolean, Float, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from pharmacy_os.core.db.base import Base, PkUuidMixin, TimestampMixin

# jsonb on Postgres, plain JSON elsewhere (SQLite tests).
_JSONB = JSON().with_variant(JSONB(), "postgresql")


class DrugInteractionORM(PkUuidMixin, TimestampMixin, Base):
    """Known interaction between two active ingredients (docs/03 drug_interactions).

    Global reference data — NOT tenant-scoped. The ingredient pair is stored canonical
    (normalized + sorted by the domain entity), so the unique constraint makes
    ``A×B`` and ``B×A`` one row and keeps the seed idempotent.
    """

    __tablename__ = "drug_interactions"
    __table_args__ = (
        UniqueConstraint("ingredient_a", "ingredient_b", name="uq_drug_interactions_pair"),
    )

    ingredient_a: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    ingredient_b: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    mechanism: Mapped[str] = mapped_column(Text, nullable=False)
    management: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)


class AiRecommendationORM(PkUuidMixin, TimestampMixin, Base):
    """Immutable audit record of one AI decision-support call (docs/03 ai_recommendations).

    Tenant-scoped by ``tenant_id`` only (no ``branch_id`` — an AI recommendation is a
    tenant-level audit fact, like ``national_sync_logs``). ``requires_review`` persists the
    output-guardrail verdict; ``accepted_by`` is the only column a use-case updates after
    insert (the human-in-the-loop sign-off).
    """

    __tablename__ = "ai_recommendations"

    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    context_type: Mapped[str] = mapped_column(String(8), nullable=False)
    context_id: Mapped[UUID | None] = mapped_column(nullable=True)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    requires_review: Mapped[bool] = mapped_column(Boolean, nullable=False)
    output: Mapped[str] = mapped_column(_JSONB, nullable=False)
    sources: Mapped[list[str]] = mapped_column(_JSONB, nullable=False, default=list)
    accepted_by: Mapped[UUID | None] = mapped_column(nullable=True)
