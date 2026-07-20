"""SQLAlchemy models for inventory. Cross-dialect (Postgres + SQLite for tests)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from pharmacy_os.core.db.base import Base, PkUuidMixin, TenantScopedMixin, TimestampMixin

_QTY = Numeric(18, 3)
_MONEY = Numeric(18, 2)


class ProductBatchORM(PkUuidMixin, TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "product_batches"
    __table_args__ = (UniqueConstraint("drug_id", "branch_id", "lot_no", name="uq_batch_lot"),)

    drug_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    lot_no: Mapped[str] = mapped_column(String(64), nullable=False)
    expiry_date: Mapped[date] = mapped_column(index=True, nullable=False)
    mfg_date: Mapped[date | None] = mapped_column()
    cost_price: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    quantity_received: Mapped[Decimal] = mapped_column(_QTY, nullable=False)


class StockMovementORM(PkUuidMixin, TenantScopedMixin, TimestampMixin, Base):
    """Append-only stock change (the source of truth for on-hand levels)."""

    __tablename__ = "stock_movements"

    drug_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    batch_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(_QTY, nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(32))
    ref_id: Mapped[UUID | None] = mapped_column()
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StockBalanceORM(PkUuidMixin, TenantScopedMixin, Base):
    """Projection of movements: on-hand per (drug, batch, branch)."""

    __tablename__ = "stock_balances"
    __table_args__ = (
        UniqueConstraint("drug_id", "batch_id", "branch_id", name="uq_balance_batch"),
    )

    drug_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    batch_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(_QTY, nullable=False, default=Decimal("0"))
