"""Pydantic request/response schemas for inventory."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from pharmacy_os.modules.inventory.application.dto import (
    DispenseInput,
    DispenseOutput,
    NearExpiryItem,
    PutAwayOutput,
    ReceiptOutput,
    ReceiveStockInput,
    ReconciliationOutput,
    StockReportItem,
)
from pharmacy_os.modules.inventory.domain import ChangLay, LocationStockRow, PickCandidate
from pharmacy_os.modules.inventory.domain.counting import CountLine, StockCount


class ReceiveStockRequest(BaseModel):
    drug_id: UUID
    # max_length khớp đúng độ rộng cột — không chặn ở đây thì Postgres ném
    # StringDataRightTruncationError và client nhận 500 thay vì 422 (PROJECT_STATE §7aq).
    lot_no: str = Field(max_length=64)
    expiry_date: date
    quantity: Decimal = Field(gt=0)
    cost_price: Decimal = Field(ge=0)
    mfg_date: date | None = None
    #: Cất thẳng vào ô ngay khi nhận. Bỏ trống = nhận xong xếp sau.
    location_id: UUID | None = None
    #: ``true`` = khởi tạo tồn kho, không phải nhập mua — xem ``ReceiveStockInput``.
    is_initial: bool = False

    def to_input(self) -> ReceiveStockInput:
        return ReceiveStockInput(
            drug_id=self.drug_id,
            lot_no=self.lot_no,
            expiry_date=self.expiry_date,
            quantity=self.quantity,
            cost_price=self.cost_price,
            mfg_date=self.mfg_date,
            location_id=self.location_id,
            is_initial=self.is_initial,
        )


class ReceiptResponse(BaseModel):
    batch_id: UUID
    drug_id: UUID
    quantity_received: Decimal
    on_hand: Decimal

    @classmethod
    def of(cls, out: ReceiptOutput) -> ReceiptResponse:
        return cls(
            batch_id=out.batch_id,
            drug_id=out.drug_id,
            quantity_received=out.quantity_received,
            on_hand=out.on_hand,
        )


class DispenseRequest(BaseModel):
    drug_id: UUID
    quantity: Decimal = Field(gt=0)
    ref_type: str | None = Field(default=None, max_length=32)
    ref_id: UUID | None = None

    def to_input(self) -> DispenseInput:
        return DispenseInput(
            drug_id=self.drug_id,
            quantity=self.quantity,
            ref_type=self.ref_type,
            ref_id=self.ref_id,
        )


class AllocationResponse(BaseModel):
    batch_id: UUID
    quantity: Decimal


class DispenseResponse(BaseModel):
    drug_id: UUID
    dispensed: Decimal
    on_hand: Decimal
    allocations: list[AllocationResponse]

    @classmethod
    def of(cls, out: DispenseOutput) -> DispenseResponse:
        return cls(
            drug_id=out.drug_id,
            dispensed=out.dispensed,
            on_hand=out.on_hand,
            allocations=[
                AllocationResponse(batch_id=a.batch_id, quantity=a.quantity)
                for a in out.allocations
            ],
        )


class OnHandResponse(BaseModel):
    drug_id: UUID
    on_hand: Decimal


class NearExpiryResponse(BaseModel):
    batch_id: UUID
    drug_id: UUID
    lot_no: str
    expiry_date: date
    quantity_received: Decimal

    @classmethod
    def of(cls, item: NearExpiryItem) -> NearExpiryResponse:
        return cls(
            batch_id=item.batch_id,
            drug_id=item.drug_id,
            lot_no=item.lot_no,
            expiry_date=item.expiry_date,
            quantity_received=item.quantity_received,
        )


class StockRowResponse(BaseModel):
    """Một lô đang còn hàng — dòng của màn Tồn kho (Sprint 10, D3).

    Chỉ có ``drug_id``, không có tên thuốc: inventory không được import catalog
    (contract ``import-linter``). Màn hình gắn tên bằng ``GET /drugs?ids=…`` —
    một lượt gọi cho cả trang, không phải một lượt mỗi dòng."""

    batch_id: UUID
    drug_id: UUID
    branch_id: UUID
    lot_no: str
    expiry_date: date
    quantity: Decimal

    @classmethod
    def of(cls, item: StockReportItem) -> StockRowResponse:
        return cls(
            batch_id=item.batch_id,
            drug_id=item.drug_id,
            branch_id=item.branch_id,
            lot_no=item.lot_no,
            expiry_date=item.expiry_date,
            quantity=item.quantity,
        )


class ReconciliationResponse(BaseModel):
    id: UUID
    branch_id: UUID
    grn_id: UUID
    po_item_id: UUID | None
    reason: str
    resolved: bool
    occurred_at: datetime

    @classmethod
    def of(cls, out: ReconciliationOutput) -> ReconciliationResponse:
        return cls(
            id=out.id,
            branch_id=out.branch_id,
            grn_id=out.grn_id,
            po_item_id=out.po_item_id,
            reason=out.reason,
            resolved=out.resolved,
            occurred_at=out.occurred_at,
        )


class PutAwayRequest(BaseModel):
    """Cất hàng của một lô vào một ô."""

    batch_id: UUID
    location_id: UUID
    quantity: Decimal = Field(gt=0)


class PutAwayResponse(BaseModel):
    batch_id: UUID
    location_id: UUID
    location_path: str
    quantity: Decimal
    #: Số hàng của lô **vẫn chưa có chỗ**. Hiện ra chứ không giấu — xem `PutAwayOutput`.
    chua_xep_o: Decimal

    @classmethod
    def of(cls, out: PutAwayOutput) -> PutAwayResponse:
        return cls(
            batch_id=out.batch_id,
            location_id=out.location_id,
            location_path=out.location_path,
            quantity=out.quantity,
            chua_xep_o=out.chua_xep_o,
        )


class PickCandidateResponse(BaseModel):
    """Một chỗ lấy được hàng — **đã sắp theo thứ tự lấy**, đừng sắp lại ở màn hình."""

    location_id: UUID
    location_path: str
    pick_order: int
    batch_id: UUID
    lot_no: str
    expiry_date: date
    quantity: Decimal

    @classmethod
    def of(cls, c: PickCandidate) -> PickCandidateResponse:
        return cls(
            location_id=c.location_id,
            location_path=c.location_path,
            pick_order=c.pick_order,
            batch_id=c.batch_id,
            lot_no=c.lot_no,
            expiry_date=c.expiry_date,
            quantity=c.quantity,
        )


class LocationStockResponse(BaseModel):
    """Một lô đang nằm trong một ô — nguồn của câu *"ô A01 có thuốc gì"*."""

    drug_id: UUID
    batch_id: UUID
    location_id: UUID
    lot_no: str
    expiry_date: date
    quantity: Decimal

    @classmethod
    def of(cls, r: LocationStockRow) -> LocationStockResponse:
        return cls(
            drug_id=r.drug_id,
            batch_id=r.batch_id,
            location_id=r.location_id,
            lot_no=r.lot_no,
            expiry_date=r.expiry_date,
            quantity=r.quantity,
        )


# ── BERAS V2 Phase 11: kiểm kê theo ô ────────────────────────────────────────────


class OpenCountRequest(BaseModel):
    """Mở phiên kiểm kê một ô."""

    location_id: UUID


class CountLineRequest(BaseModel):
    """Ghi số đếm được của một lô. Đếm lại cùng lô thì **đè**, không cộng dồn."""

    batch_id: UUID
    counted_qty: Decimal = Field(ge=0)


class CountLineResponse(BaseModel):
    """Một dòng đếm.

    ``system_qty``/``lech`` là ``None`` khi phiên **chưa nộp** — cố ý không thay bằng 0, vì
    0 đọc y hệt "đã chốt và khớp".
    """

    id: UUID
    batch_id: UUID
    counted_qty: Decimal
    system_qty: Decimal | None
    lech: Decimal | None

    @classmethod
    def of(cls, d: CountLine) -> CountLineResponse:
        return cls(
            id=d.id,
            batch_id=d.batch_id,
            counted_qty=d.counted_qty,
            system_qty=d.system_qty,
            lech=d.lech,
        )


class StockCountResponse(BaseModel):
    """Một phiên kiểm kê kèm dòng.

    Trả **cả hai** ``counted_by`` và ``decided_by``: người đếm được phép tự duyệt phiếu
    mình, nên phải nhìn ra được khi hai tên trùng nhau.
    """

    id: UUID
    location_id: UUID
    status: str
    counted_by: UUID
    decided_by: UUID | None
    created_at: datetime
    submitted_at: datetime | None
    decided_at: datetime | None
    lines: list[CountLineResponse]

    @classmethod
    def of(cls, p: StockCount) -> StockCountResponse:
        return cls(
            id=p.id,
            location_id=p.location_id,
            status=str(p.status),
            counted_by=p.counted_by,
            decided_by=p.decided_by,
            created_at=p.created_at,
            submitted_at=p.submitted_at,
            decided_at=p.decided_at,
            lines=[CountLineResponse.of(d) for d in p.lines],
        )


class DongLoTrinhResponse(BaseModel):
    """Một dòng cần nhặt tại một ô."""

    drug_id: UUID
    lot_no: str
    expiry_date: date
    quantity: Decimal


class ChangLayResponse(BaseModel):
    """Một chặng: tới **một ô**, nhặt những gì cần ở đó (BERAS V2 Phase 4)."""

    location_id: UUID
    location_path: str
    pick_order: int
    dong: list[DongLoTrinhResponse]

    @classmethod
    def of(cls, c: ChangLay) -> ChangLayResponse:
        return cls(
            location_id=c.location_id,
            location_path=c.location_path,
            pick_order=c.pick_order,
            dong=[
                DongLoTrinhResponse(drug_id=d, lot_no=lo, expiry_date=hsd, quantity=sl)
                for d, lo, hsd, sl in c.dong
            ],
        )


class DongYeuCauRequest(BaseModel):
    drug_id: UUID
    quantity: Decimal = Field(gt=0)


class LoTrinhRequest(BaseModel):
    """Giỏ cần lấy. `POST` chứ không `GET`: một giỏ hai chục mã nhét vào query string sẽ
    chạm giới hạn độ dài URL của proxy, và hỏng ở đó thì hiện ra dưới dạng lỗi mạng khó
    hiểu chứ không phải một thông báo đọc được."""

    dong: list[DongYeuCauRequest] = Field(min_length=1)


class LoTrinhResponse(BaseModel):
    chang: list[ChangLayResponse]
    #: Mã KHÔNG lấy đủ được từ các ô. Rỗng là bình thường. `where_is` trả rỗng nghĩa là
    #: thuốc chưa được xếp ô — khác hẳn "kho hết hàng", và màn hình phải nói ra khác biệt đó.
    thieu: list[UUID]
