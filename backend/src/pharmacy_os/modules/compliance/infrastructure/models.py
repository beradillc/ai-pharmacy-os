"""SQLAlchemy models for compliance. Cross-dialect (Postgres + SQLite for tests)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, DateTime, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from pharmacy_os.core.db.base import Base, PkUuidMixin, TenantScopedMixin, TimestampMixin


class ControlledLedgerEntryORM(PkUuidMixin, TenantScopedMixin, TimestampMixin, Base):
    """Sổ thuốc kiểm soát đặc biệt (docs/13 mục C.2.1) — hợp nhất Phụ lục VIII + XXI.

    Immutable theo domain rule — bảng này chỉ INSERT, không có cột nào được service cập nhật
    sau khi ghi (TT 20/2017 Điều 18: không hard-delete/sửa trong thời gian lưu trữ).
    """

    __tablename__ = "controlled_ledger_entries"

    drug_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    lot_no: Mapped[str] = mapped_column(String(64), nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    transaction_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_or_destination: Mapped[str] = mapped_column(String(255), nullable=False)
    document_no: Mapped[str] = mapped_column(String(64), nullable=False)
    prescription_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class TenantComplianceConfigORM(PkUuidMixin, TimestampMixin, Base):
    """Mã cơ sở do Cục QLD cấp — 1 dòng/tenant (docs/13 mục F, entity mới)."""

    __tablename__ = "tenant_compliance_configs"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tenant_compliance_configs_tenant"),)

    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    ma_co_so_ban_le: Mapped[str] = mapped_column(String(12), nullable=False)
    ma_co_so_ban_buon: Mapped[str | None] = mapped_column(String(12), nullable=True)
