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
from pharmacy_os.modules.inventory.domain import LocationStockRow, PickCandidate


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

    def to_input(self) -> ReceiveStockInput:
        return ReceiveStockInput(
            drug_id=self.drug_id,
            lot_no=self.lot_no,
            expiry_date=self.expiry_date,
            quantity=self.quantity,
            cost_price=self.cost_price,
            mfg_date=self.mfg_date,
            location_id=self.location_id,
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
