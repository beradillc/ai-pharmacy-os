"""Inventory persistence ports (implemented by infrastructure)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.inventory.domain.counting import StockCount
from pharmacy_os.modules.inventory.domain.entities import (
    ProductBatch,
    StockMovement,
    StockReconciliationNeeded,
)
from pharmacy_os.modules.inventory.domain.fefo import BatchAvailability


@dataclass(frozen=True, slots=True)
class BatchStockRow:
    """One batch's current on-hand, as read for the Sprint 7 stock report.

    ``quantity`` is the live ``stock_balances`` projection, not
    ``quantity_received`` — the report shows what's actually left, same
    source as :meth:`BalanceRepository.on_hand`."""

    batch_id: UUID
    drug_id: UUID
    branch_id: UUID
    lot_no: str
    expiry_date: date
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class DrugOnHandRow:
    """Total on-hand of a drug at a branch, summed across its batches.

    The bulk counterpart of :meth:`BalanceRepository.on_hand` (single drug) —
    the analytics reorder run needs current stock for every drug at once, and a
    per-drug round-trip would be N queries. Only drugs with positive stock appear."""

    drug_id: UUID
    branch_id: UUID
    on_hand: Decimal


class BatchRepository(Protocol):
    async def add(self, batch: ProductBatch) -> None: ...

    async def update(self, batch: ProductBatch) -> None:
        """Persist ``quantity_received``/``cost_price`` after :meth:`ProductBatch.merge_receipt`."""
        ...

    async def get(self, batch_id: UUID) -> ProductBatch | None: ...

    async def find_by_lot(self, drug_id: UUID, branch_id: UUID, lot_no: str) -> ProductBatch | None:
        """Return the batch matching ``(drug_id, branch_id, lot_no)`` if one exists.

        Mirrors the ``uq_batch_lot`` uniqueness so a caller can check for a lot
        collision *before* inserting, rather than provoking an integrity error.
        """
        ...

    async def availabilities(
        self, drug_id: UUID, branch_id: UUID, *, not_expired_on: date
    ) -> list[BatchAvailability]: ...

    async def near_expiry(self, branch_id: UUID, *, before: date) -> list[ProductBatch]: ...

    async def stock_report(
        self,
        tenant_id: UUID,
        *,
        branch_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[BatchStockRow]:
        """Page of batches with on-hand > 0, tenant-wide (or narrowed to one branch),
        soonest-expiring first, ``batch_id`` as the pagination tie-break."""
        ...


class MovementRepository(Protocol):
    async def add(self, movement: StockMovement) -> None:
        """Append one movement.

        Raises :class:`DuplicateMovementError` when a movement for the same
        ``(tenant, ref_type, ref_id, batch_id)`` already exists — the store's own
        uniqueness, which is what makes idempotency hold under concurrency where
        :meth:`exists_for_ref` alone cannot (audit B-02). Movements without a
        ``ref_id`` are never constrained: they carry no identity to be duplicate of.
        """
        ...

    async def exists_for_ref(self, ref_type: str, ref_id: UUID) -> bool:
        """True if any movement already references *(ref_type, ref_id)* (idempotency).

        A **fast path only**, never the guarantee: between this read and the write
        that follows, another transaction can insert. The guarantee lives in
        :meth:`add`'s :class:`DuplicateMovementError`; callers must handle it too.
        """
        ...


class BalanceRepository(Protocol):
    async def adjust(
        self, drug_id: UUID, batch_id: UUID, branch_id: UUID, tenant_id: UUID, delta: Decimal
    ) -> Decimal:
        """Apply *delta* to the (drug, batch, branch) balance; return new on-hand.

        Two guarantees the caller may rely on, both enforced by the store rather
        than by a preceding read (audit B-01/B-04):

        * **No lost update.** Concurrent adjusts compose — 100 − 10 − 10 is 80, not
          90. Read-then-write in application code cannot promise this.
        * **Never negative.** A *delta* that would drive the balance below zero is
          refused with :class:`InsufficientStockError` carrying the quantity that
          *was* available. A pharmacy cannot hand over stock it does not have, and
          a ledger that goes negative is a ledger nobody can use.
        """

    async def on_hand(self, drug_id: UUID, branch_id: UUID) -> Decimal:
        """Total on-hand across all batches of a drug at a branch."""

    async def for_batch(self, batch_id: UUID) -> Decimal:
        """Tồn hiện tại của MỘT lô — vế phải của bất biến hai sổ (Phase 2).

        Đọc thẳng ``stock_balances``, cùng nguồn với :meth:`on_hand`. Trả ``0`` khi lô chưa
        có dòng số dư nào, không ném lỗi: một lô vừa tạo mà chưa có chuyển động nào là
        trạng thái hợp lệ.
        """
        ...

    async def on_hand_by_drug(self, branch_id: UUID) -> list[DrugOnHandRow]:
        """On-hand per drug at a branch (all drugs with positive stock), summed in
        SQL. Bulk read for the analytics reorder run — see :class:`DrugOnHandRow`."""
        ...


class StockReconciliationRepository(Protocol):
    async def add(self, record: StockReconciliationNeeded) -> None:
        """Persist a reconciliation flag."""
        ...

    async def get(self, record_id: UUID, tenant_id: UUID) -> StockReconciliationNeeded | None: ...

    async def update(self, record: StockReconciliationNeeded) -> None:
        """Persist the ``resolved`` transition (the only field :meth:`resolve` changes)."""
        ...

    async def list(
        self,
        tenant_id: UUID,
        branch_id: UUID,
        *,
        resolved: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[StockReconciliationNeeded]:
        """List a branch's discrepancies, newest first; ``resolved=None`` returns both."""
        ...


@dataclass(frozen=True, slots=True)
class LocationInfo:
    """Sự thật về một ô mà ``inventory`` cần — đúng ba thứ, không hơn.

    ``path`` để hiện cho người đứng quầy, ``pick_order`` để sắp đường đi, ``is_active`` để
    từ chối cất hàng vào chỗ đã khai tử. Không mang ``name``, không mang cây con: lấy thừa
    là buộc ``inventory`` biết về hình dạng sơ đồ kho, thứ nó không có việc gì phải biết.
    """

    location_id: UUID
    path: str
    pick_order: int
    is_active: bool


class LocationInfoProvider(Protocol):
    """Read-port cho sơ đồ kho, để ``inventory`` không import module ``location``.

    Cài ở composition root (adapter trên ``LocationService``) — cùng khuôn
    ``DrugInfoProvider`` của ``sales``. Trả ``None`` khi ô không tồn tại trong chi nhánh.
    """

    async def get(
        self, location_id: UUID, tenant_id: UUID, branch_id: UUID
    ) -> LocationInfo | None: ...

    async def many(
        self, location_ids: frozenset[UUID], tenant_id: UUID, branch_id: UUID
    ) -> dict[UUID, LocationInfo]:
        """Nhiều ô trong MỘT lượt.

        Bắt buộc phải có bên cạnh :meth:`get`: một thuốc nằm ở năm ô thì hỏi năm lượt là
        năm vòng đi-về cho một màn hình mà thu ngân đang đứng chờ.
        """
        ...


@dataclass(frozen=True, slots=True)
class TomTatO:
    """Tóm tắt một ô cho **sơ đồ trực quan** (BERAS V2 Phase 12, mức 1).

    Ba con số trả lời ba câu người đứng kho hỏi khi nhìn sơ đồ: *ô này có bận không*
    (``so_lo``), *bận bao nhiêu* (``tong_so_luong``), *có gì sắp hết hạn không*
    (``hsd_gan_nhat``).

    Cố ý **không** có "sức chứa" hay "phần trăm đầy": kho chưa khai sức chứa của ô nào, và
    một phần trăm tính từ con số không có thật là **tệ hơn không hiện gì** — người ta tin
    vào nó.
    """

    location_id: UUID
    so_lo: int
    tong_so_luong: Decimal
    hsd_gan_nhat: date


class StockAtLocationRepository(Protocol):
    """Sổ **nằm ở đâu** — projection thứ hai, luôn ≤ ``stock_balances``."""

    async def put_away(
        self, *, drug_id: UUID, batch_id: UUID, location_id: UUID, delta: Decimal
    ) -> None:
        """Cộng dồn *delta* vào một (lô, ô). Tạo dòng nếu chưa có.

        Cộng dồn chứ không gán đè: hai lượt cất cùng một lô vào cùng một ô là chuyện bình
        thường (nhận hàng hai đợt), và gán đè sẽ **nuốt mất đợt trước** trong im lặng.
        """
        ...

    async def total_for_batch(self, batch_id: UUID) -> Decimal:
        """Tổng đã xếp ô của một lô — vế trái của bất biến hai sổ."""
        ...

    async def rows_for_drug(self, drug_id: UUID) -> Sequence[LocationStockRow]:
        """Mọi (lô, ô) đang giữ hàng của một thuốc. Chỉ trả dòng có ``quantity > 0``."""
        ...

    async def tom_tat_moi_o(self) -> Sequence[TomTatO]:
        """Mỗi ô **đang giữ hàng** một dòng tóm tắt — nguồn của sơ đồ trực quan (Phase 12).

        🔴 Vì sao là một truy vấn riêng chứ không gọi :meth:`rows_at_location` cho từng ô:
        một kho vài trăm ô nghĩa là vài trăm lượt đi-về cho **một** màn hình. Gộp ở tầng
        CSDL là chỗ duy nhất làm được rẻ.

        Chỉ trả ô **có hàng**. Ô trống không có dòng — màn hình biết chúng trống bằng cách
        đối chiếu với sơ đồ, và *"không có dòng"* rẻ hơn *"dòng với số 0"* cho một kho mà
        phần lớn ô trống.
        """
        ...

    async def rows_at_location(self, location_id: UUID) -> Sequence[LocationStockRow]:
        """Ô này đang giữ những lô nào — nguồn của câu hỏi *"ô A01 có thuốc gì"*."""
        ...


@dataclass(frozen=True, slots=True)
class LocationStockRow:
    """Một dòng của sổ vị trí, đã ghép sẵn thông tin lô để khỏi phải tra lần hai."""

    drug_id: UUID
    batch_id: UUID
    location_id: UUID
    lot_no: str
    expiry_date: date
    quantity: Decimal


class StockCountRepository(Protocol):
    """Phiên kiểm kê. Lưu **cả cụm** (phiên + dòng) — dòng không có đời sống riêng."""

    async def add(self, count: StockCount) -> None:
        """Lưu một phiên mới cùng toàn bộ dòng của nó."""
        ...

    async def get(self, count_id: UUID) -> StockCount | None:
        """Đọc một phiên kèm dòng. ``None`` nếu không thuộc chi nhánh đang gọi."""
        ...

    async def update(self, count: StockCount) -> None:
        """Ghi lại phiên sau khi đổi trạng thái hoặc thêm dòng."""
        ...

    async def list(self, *, status: str | None, limit: int, offset: int) -> Sequence[StockCount]:
        """Danh sách phiên của chi nhánh, mới nhất trước."""
        ...
