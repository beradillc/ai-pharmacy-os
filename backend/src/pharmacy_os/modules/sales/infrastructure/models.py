"""SQLAlchemy models for sales. Cross-dialect (Postgres + SQLite for tests)."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pharmacy_os.core.db.base import Base, PkUuidMixin, TenantScopedMixin, TimestampMixin


class SalesOrderORM(PkUuidMixin, TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "sales_orders"
    __table_args__ = (UniqueConstraint("tenant_id", "client_uuid", name="uq_sale_client_uuid"),)

    client_uuid: Mapped[str] = mapped_column(String(64), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VND")
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    prescription_ref: Mapped[UUID | None] = mapped_column(nullable=True)

    lines: Mapped[list[SaleLineORM]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    payments: Mapped[list[PaymentORM]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SaleLineORM(PkUuidMixin, Base):
    __tablename__ = "sale_lines"

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("sales_orders.id", ondelete="CASCADE"), index=True
    )
    drug_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    requires_prescription: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    returned_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 3), default=Decimal("0"), nullable=False
    )

    order: Mapped[SalesOrderORM] = relationship(back_populates="lines")


class PaymentORM(PkUuidMixin, Base):
    __tablename__ = "sale_payments"

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("sales_orders.id", ondelete="CASCADE"), index=True
    )
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    order: Mapped[SalesOrderORM] = relationship(back_populates="payments")
