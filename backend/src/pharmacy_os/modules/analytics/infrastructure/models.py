"""SQLAlchemy model for analytics. Cross-dialect (Postgres + SQLite for tests)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from pharmacy_os.core.db.base import Base, PkUuidMixin, TenantScopedMixin


class ReorderSuggestionORM(PkUuidMixin, TenantScopedMixin, Base):
    """One drug×branch reorder suggestion (projection of a run, plus its lifecycle).

    ``drug_id``/``supplier_id`` are plain UUIDs, no cross-module FK (module
    independence), same convention as ``sales.SaleLine.drug_id``. ``calculated_at`` is
    the run timestamp; there is no ``TimestampMixin`` because a suggestion is a
    snapshot, not a mutable record with an update trail."""

    __tablename__ = "reorder_suggestions"

    drug_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    avg_daily_velocity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    reorder_point: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    on_hand_at_calc: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    suggested_qty: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    supplier_id: Mapped[UUID | None] = mapped_column(nullable=True)
    po_id: Mapped[UUID | None] = mapped_column(nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
