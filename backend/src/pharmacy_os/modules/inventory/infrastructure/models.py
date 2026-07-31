"""SQLAlchemy models for inventory. Cross-dialect (Postgres + SQLite for tests)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
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
    __table_args__ = (
        Index(
            "uq_movement_ref_batch",
            "tenant_id",
            "ref_type",
            "ref_id",
            "batch_id",
            unique=True,
            postgresql_where=text("ref_id IS NOT NULL"),
            sqlite_where=text("ref_id IS NOT NULL"),
        ),
    )
    """Replay of the same sale/GRN moves stock **once** — enforced here, not by the
    ``SELECT`` in :meth:`MovementRepository.exists_for_ref` (audit B-02).

    ``batch_id`` belongs in the key and leaving it out would be the expensive
    mistake: one FEFO dispense legitimately spans several lots and writes one row
    per lot, all sharing a ``ref_id``. Keyed without it, the constraint would
    reject correct pharmacy work — the opposite of the bug it exists to stop.

    Partial on ``ref_id IS NOT NULL`` because a movement without a reference has no
    identity to be a duplicate of (a manual receive carries ``ref_type='GRN'`` and
    no id). Postgres would treat those NULLs as distinct anyway; saying so
    explicitly keeps the index small and keeps SQLite — where the test suite runs —
    behaving the same way.
    """

    drug_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    batch_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(_QTY, nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(32))
    ref_id: Mapped[UUID | None] = mapped_column()
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    #: 🔴 HAI CỘT DUY NHẤT của Phase 2 đụng vào một bảng đã có (Chain duyệt 2026-07-31 qua
    #: GĐ). Nullable: mọi dòng có từ trước để ``NULL``, đọc đúng nghĩa *"không rõ vị trí"* —
    #: không cần backfill, không có dòng nào phải đoán.
    #:
    #: Vì sao là CỘT chứ không phải bảng phụ nối 1-1: bảng phụ bắt mọi truy vấn theo vị trí
    #: phải nối bảng, và tạo ra khả năng một chuyển động tồn tại **mà không có dòng vị trí
    #: đi kèm** — đúng loại lệch im lặng dự án này đã phải đi vá nhiều lần. Trên Postgres,
    #: ``ADD COLUMN ... NULL`` là thao tác tức thì, không viết lại bảng.
    #:
    #: Không đặt khoá ngoại tới ``locations``: giữ ``inventory`` độc lập với module
    #: ``location``, cùng lý do ``grn_id`` ở ``stock_reconciliation_needed`` là UUID trần.
    from_location_id: Mapped[UUID | None] = mapped_column(nullable=True)
    to_location_id: Mapped[UUID | None] = mapped_column(nullable=True)


class StockBalanceORM(PkUuidMixin, TenantScopedMixin, Base):
    """Projection of movements: on-hand per (drug, batch, branch)."""

    __tablename__ = "stock_balances"
    __table_args__ = (
        UniqueConstraint("drug_id", "batch_id", "branch_id", name="uq_balance_batch"),
    )

    drug_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    batch_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(_QTY, nullable=False, default=Decimal("0"))


class StockAtLocationORM(PkUuidMixin, TenantScopedMixin, Base):
    """Projection THỨ HAI: hàng của một lô đang nằm ở ô nào, bao nhiêu.

    🔴 Cố ý **không** đụng vào ``stock_balances``. Thêm ``location_id`` vào đó sẽ vỡ khoá
    ``uq_balance_batch (drug_id, batch_id, branch_id)`` — vì tồn theo vị trí nghĩa là một lô
    nằm ở nhiều chỗ, tức đổi **hạt** của projection đang chạy. FEFO, báo cáo tồn và đề xuất
    nhập hàng đều đọc bảng cũ; đổi hạt của nó là phá cả ba cùng lúc.

    Hai sổ trả lời hai câu hỏi khác nhau:
      · ``stock_balances``     — *có bao nhiêu*  (nguồn sự thật, đã có từ trước)
      · ``stock_at_location``  — *nằm ở đâu*     (mới, ≤ sổ trên)

    Bất biến: tổng theo lô của bảng này **≤** tồn của lô trong ``stock_balances``. Phần chênh
    là hàng **chưa xếp ô** — hợp lệ và bình thường (hàng vừa nhận, còn trên xe đẩy), và phải
    hiện ra màn hình chứ không giấu đi.
    """

    __tablename__ = "stock_at_location"
    __table_args__ = (
        UniqueConstraint("branch_id", "batch_id", "location_id", name="uq_stock_at_location"),
        Index("ix_stock_at_location_drug", "branch_id", "drug_id"),
        Index("ix_stock_at_location_loc", "branch_id", "location_id"),
    )

    drug_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    batch_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    #: UUID trần, không FK — giữ `inventory` độc lập với module `location`.
    location_id: Mapped[UUID] = mapped_column(nullable=False)
    quantity: Mapped[Decimal] = mapped_column(_QTY, nullable=False, default=Decimal("0"))


class StockReconciliationNeededORM(PkUuidMixin, TenantScopedMixin, TimestampMixin, Base):
    """Audit-only: a confirmed GRN whose inventory stock-in didn't fully land.

    ``grn_id``/``po_item_id`` are cross-module references to procurement, kept as
    plain UUIDs (no FK) so inventory stays independent of procurement. No resolve
    workflow yet — ``resolved`` defaults ``False``.
    """

    __tablename__ = "stock_reconciliation_needed"

    grn_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    po_item_id: Mapped[UUID | None] = mapped_column(nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
