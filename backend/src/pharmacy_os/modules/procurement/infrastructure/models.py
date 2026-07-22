"""SQLAlchemy models for procurement. Cross-dialect (Postgres + SQLite for tests).

``GoodsReceiptItemORM.po_item_id`` carries a real FK to ``purchase_order_items`` —
this is an **intra-module** reference (both tables belong to ``procurement``), not
a cross-module one, so it's safe to FK unconditionally (unlike ``drug_id``, a
cross-module reference to ``catalog``, deliberately left un-FK'd here — same
convention as ``sales.SaleLine.drug_id``/``prescription...drug_id``).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pharmacy_os.core.db.base import Base, PkUuidMixin, TenantScopedMixin, TimestampMixin


class SupplierORM(PkUuidMixin, TimestampMixin, Base):
    """Supplier master record — tenant-scoped (not branch-scoped, like ``customers``)."""

    __tablename__ = "suppliers"

    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PurchaseOrderORM(PkUuidMixin, TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "purchase_orders"

    supplier_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list[PurchaseOrderItemORM]] = relationship(
        back_populates="purchase_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PurchaseOrderItemORM(PkUuidMixin, Base):
    __tablename__ = "purchase_order_items"

    purchase_order_id: Mapped[UUID] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True
    )
    drug_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    quantity_ordered: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    quantity_received: Mapped[Decimal] = mapped_column(
        Numeric(18, 3), nullable=False, default=Decimal("0")
    )

    purchase_order: Mapped[PurchaseOrderORM] = relationship(back_populates="items")


class GoodsReceiptORM(PkUuidMixin, TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "goods_receipts"

    po_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    received_by: Mapped[UUID] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    items: Mapped[list[GoodsReceiptItemORM]] = relationship(
        back_populates="goods_receipt",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class GoodsReceiptItemORM(PkUuidMixin, Base):
    __tablename__ = "goods_receipt_items"

    goods_receipt_id: Mapped[UUID] = mapped_column(
        ForeignKey("goods_receipts.id", ondelete="CASCADE"), index=True
    )
    po_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("purchase_order_items.id"), index=True, nullable=False
    )
    drug_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    lot_no: Mapped[str] = mapped_column(String(64), nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    mfg_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    goods_receipt: Mapped[GoodsReceiptORM] = relationship(back_populates="items")
