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
    # Plain UUID, no FK to crm.customers: sales must stay independent of crm
    # (module-independence), same convention as prescription_ref / drug_id.
    customer_id: Mapped[UUID | None] = mapped_column(index=True, nullable=True)
    # Who completed the sale. Plain UUID, no FK to iam.users for the same
    # module-independence reason; indexed because the revenue report filters on it.
    sold_by_user_id: Mapped[UUID | None] = mapped_column(index=True, nullable=True)

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
    gateway_ref: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    """The gateway's own transaction id, ``NULL`` for cash/card. ``unique`` is the
    idempotency guard at the storage layer against a gateway (Sprint 8 mục 4/4,
    ``payment_vnpay``) calling its webhook back more than once for one transaction —
    a second insert attempt with the same value fails the constraint rather than
    silently doubling the payment. Standard SQL treats every ``NULL`` as distinct
    from every other, so cash/card rows (always ``NULL``) never collide with it."""

    order: Mapped[SalesOrderORM] = relationship(back_populates="payments")
