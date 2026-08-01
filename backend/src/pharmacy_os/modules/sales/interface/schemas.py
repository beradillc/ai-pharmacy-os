"""Pydantic request/response schemas for sales."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from pharmacy_os.modules.sales.application.dto import (
    CreateSaleInput,
    PaymentInput,
    ReceiptSummaryDTO,
    RegisterReturnInput,
    SaleLineInput,
    SaleOutput,
    VnpayInitiateOutput,
)
from pharmacy_os.modules.sales.domain import AllergyRisk, PaymentMethod, SalesOrderListRow


class SaleLineRequest(BaseModel):
    drug_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    requires_prescription: bool = False


class PaymentRequest(BaseModel):
    method: PaymentMethod
    amount: Decimal = Field(ge=0)


class CreateSaleRequest(BaseModel):
    client_uuid: str = Field(min_length=1, max_length=64)
    lines: list[SaleLineRequest] = Field(min_length=1)
    payments: list[PaymentRequest] = Field(default_factory=list)
    prescription_ref: UUID | None = None
    customer_id: UUID | None = None
    currency: str = Field(default="VND", max_length=8)  # độ rộng cột sales_orders.currency
    #: Lý do người bán vẫn bán dù có cảnh báo dị ứng (Đ-6). Chỉ cần khi đơn có xung đột.
    #: Chuỗi toàn khoảng trắng KHÔNG tính là đã xác nhận — domain chặn, không phải Field.
    allergy_acknowledgement: str | None = Field(default=None, max_length=500)
    price_override_reason: str | None = Field(default=None, max_length=255)

    def to_input(self) -> CreateSaleInput:
        return CreateSaleInput(
            client_uuid=self.client_uuid,
            lines=[
                SaleLineInput(
                    drug_id=ln.drug_id,
                    quantity=ln.quantity,
                    unit_price=ln.unit_price,
                    requires_prescription=ln.requires_prescription,
                )
                for ln in self.lines
            ],
            payments=[PaymentInput(method=p.method, amount=p.amount) for p in self.payments],
            prescription_ref=self.prescription_ref,
            customer_id=self.customer_id,
            currency=self.currency,
            allergy_acknowledgement=self.allergy_acknowledgement,
            price_override_reason=self.price_override_reason,
        )


class AllergyCheckRequest(BaseModel):
    """Hỏi cảnh báo dị ứng cho một giỏ hàng đang dựng (Đ-7)."""

    customer_id: UUID
    drug_ids: list[UUID] = Field(min_length=1)


class AllergyCheckResponse(BaseModel):
    """Phán quyết dị ứng cho quầy.

    ``consent_granted=False`` nghĩa là **phép kiểm không chạy** (khách chưa đồng ý cho
    xử lý dữ liệu sức khoẻ), KHÔNG phải "đã kiểm và sạch" — giao diện phải hiện hai
    trạng thái đó khác nhau, nếu không nó nói dối người dùng.

    ``checked=False`` khi hệ thống chưa nối cổng dị ứng hoặc không tìm thấy khách.
    """

    checked: bool
    consent_granted: bool = False
    conflict_count: int = 0
    worst_severity: str | None = None

    @classmethod
    def of(cls, risk: AllergyRisk | None) -> AllergyCheckResponse:
        if risk is None:
            return cls(checked=False)
        return cls(
            checked=True,
            consent_granted=risk.consent_granted,
            conflict_count=risk.conflict_count,
            worst_severity=risk.worst_severity,
        )


class VnpayInitiateResponse(BaseModel):
    order_id: UUID
    payment_url: str

    @classmethod
    def of(cls, out: VnpayInitiateOutput) -> VnpayInitiateResponse:
        return cls(order_id=out.order_id, payment_url=out.payment_url)


class RegisterReturnRequest(BaseModel):
    line_id: UUID
    quantity: Decimal = Field(gt=0)

    def to_input(self) -> RegisterReturnInput:
        return RegisterReturnInput(line_id=self.line_id, quantity=self.quantity)


class SaleLineResponse(BaseModel):
    id: UUID
    drug_id: UUID
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    requires_prescription: bool
    returned_quantity: Decimal


class SaleResponse(BaseModel):
    id: UUID
    client_uuid: str
    status: str
    currency: str
    subtotal: Decimal
    paid_total: Decimal
    prescription_ref: UUID | None
    customer_id: UUID | None
    lines: list[SaleLineResponse]

    @classmethod
    def of(cls, out: SaleOutput) -> SaleResponse:
        return cls(
            id=out.id,
            client_uuid=out.client_uuid,
            status=out.status,
            currency=out.currency,
            subtotal=out.subtotal,
            paid_total=out.paid_total,
            prescription_ref=out.prescription_ref,
            customer_id=out.customer_id,
            lines=[
                SaleLineResponse(
                    id=ln.id,
                    drug_id=ln.drug_id,
                    quantity=ln.quantity,
                    unit_price=ln.unit_price,
                    line_total=ln.line_total,
                    requires_prescription=ln.requires_prescription,
                    returned_quantity=ln.returned_quantity,
                )
                for ln in out.lines
            ],
        )


class SaleListItemResponse(BaseModel):
    """One line of the till list — deliberately **not** :class:`SaleResponse`.

    No ``lines`` array: a day's list of orders would otherwise carry every item of
    every order, which is the payload the screen least needs and most pays for. The
    detail view already fetches one order in full via ``GET /sales/{id}``.
    """

    id: UUID
    branch_id: UUID
    created_at: datetime
    status: str
    currency: str
    subtotal: Decimal
    paid_total: Decimal
    line_count: int
    customer_id: UUID | None
    sold_by_user_id: UUID | None

    @classmethod
    def of(cls, row: SalesOrderListRow) -> SaleListItemResponse:
        return cls(
            id=row.order_id,
            branch_id=row.branch_id,
            created_at=row.created_at,
            status=row.status,
            currency=row.currency,
            subtotal=row.subtotal,
            paid_total=row.paid_total,
            line_count=row.line_count,
            customer_id=row.customer_id,
            sold_by_user_id=row.sold_by_user_id,
        )


class ReceiptFormat(StrEnum):
    """Delivery formats for ``GET /sales/{id}/receipt``."""

    JSON = "json"
    THERMAL_K80 = "thermal_k80"
    PDF_A5 = "pdf_a5"
    PDF_A4 = "pdf_a4"
    #: PDF rộng đúng 80mm, dài theo nội dung — đường in MẶC ĐỊNH của quầy từ 2026-08-01
    #: (Chain chốt). Trình duyệt không dò được máy in nhiệt, và tệp 80mm phục vụ được cả
    #: hai trường hợp — xem `render_pdf`.
    PDF_K80 = "pdf_k80"


class ReceiptLineResponse(BaseModel):
    drug_id: UUID
    name: str
    unit: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class ReceiptPaymentResponse(BaseModel):
    method: PaymentMethod
    amount: Decimal


class ReceiptResponse(BaseModel):
    order_id: UUID
    tenant_id: UUID
    branch_id: UUID
    created_at: datetime
    client_uuid: str
    currency: str
    status: str
    lines: list[ReceiptLineResponse]
    payments: list[ReceiptPaymentResponse]
    subtotal: Decimal
    paid_total: Decimal
    change_amount: Decimal
    prescription_ref: UUID | None
    #: `None` = không tra được người bán (đơn cũ, hoặc người bán đã bị xoá).
    sold_by_name: str | None = None

    @classmethod
    def of(cls, receipt: ReceiptSummaryDTO) -> ReceiptResponse:
        return cls(
            order_id=receipt.order_id,
            tenant_id=receipt.tenant_id,
            branch_id=receipt.branch_id,
            created_at=receipt.created_at,
            client_uuid=receipt.client_uuid,
            currency=receipt.currency,
            status=receipt.status,
            lines=[
                ReceiptLineResponse(
                    drug_id=ln.drug_id,
                    name=ln.name,
                    unit=ln.unit,
                    quantity=ln.quantity,
                    unit_price=ln.unit_price,
                    line_total=ln.line_total,
                )
                for ln in receipt.lines
            ],
            payments=[
                ReceiptPaymentResponse(method=p.method, amount=p.amount) for p in receipt.payments
            ],
            subtotal=receipt.subtotal,
            paid_total=receipt.paid_total,
            change_amount=receipt.change_amount,
            prescription_ref=receipt.prescription_ref,
            sold_by_name=receipt.sold_by_name,
        )
