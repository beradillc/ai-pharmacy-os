"""Pydantic request/response schemas for compliance, enforcing docs/13_COMPLIANCE_SPEC.md mục C.3.

Requests give an immediate 422 on malformed input independent of the domain-level rule in
``compliance.domain.rules`` (defense in depth — the domain rule remains the source of truth
for non-HTTP callers such as the cross-module composition root).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from pharmacy_os.modules.compliance.application.dto import (
    ControlledLedgerEntryOutput,
    CustomerDetailInput,
    NationalSyncLogOutput,
    PushSyncInput,
    RecordControlledEntryInput,
    SetTenantComplianceConfigInput,
    TenantComplianceConfigOutput,
)
from pharmacy_os.modules.compliance.domain import (
    ControlledSubstanceCategory,
    LedgerDirection,
    SyncPayloadType,
)

_PRESCRIPTION_RETAINED_CATEGORIES = (
    ControlledSubstanceCategory.GAY_NGHIEN,
    ControlledSubstanceCategory.HUONG_THAN,
)


class CustomerDetailRequest(BaseModel):
    """Phụ lục XXI — chỉ tên + địa chỉ, KHÔNG có trường CCCD/CMND (mẫu gốc không có cột này)."""

    patient_name: str = Field(min_length=1, max_length=255)
    patient_address: str = Field(min_length=1, max_length=500)


class RecordControlledEntryRequest(BaseModel):
    drug_id: UUID
    category: ControlledSubstanceCategory
    direction: LedgerDirection
    quantity: Decimal = Field(gt=0)
    lot_no: str = Field(min_length=1, max_length=64)
    expiry_date: date
    transaction_at: datetime
    source_or_destination: str = Field(min_length=1, max_length=255)
    document_no: str = Field(min_length=1, max_length=64)
    prescription_code: str | None = None
    customer: CustomerDetailRequest | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _enforce_controlled_sale_rule(self) -> RecordControlledEntryRequest:
        """docs/13 mục C.3 rule 2 — chỉ áp dụng chiều XUAT của thuốc kiểm soát đặc biệt."""
        if self.direction is not LedgerDirection.XUAT:
            return self
        if self.category is ControlledSubstanceCategory.NONE:
            return self
        if self.customer is None:
            raise ValueError(
                "Thuốc kiểm soát đặc biệt bán ra cần thông tin khách hàng "
                "(Phụ lục XXI: tên + địa chỉ)"
            )
        if self.category in _PRESCRIPTION_RETAINED_CATEGORIES and not self.prescription_code:
            raise ValueError(
                "Thuốc gây nghiện/hướng thần bán ra cần lưu prescription_code (Điều 15.1.c)"
            )
        return self

    def to_input(self) -> RecordControlledEntryInput:
        return RecordControlledEntryInput(
            drug_id=self.drug_id,
            category=self.category,
            direction=self.direction,
            quantity=self.quantity,
            lot_no=self.lot_no,
            expiry_date=self.expiry_date,
            transaction_at=self.transaction_at,
            source_or_destination=self.source_or_destination,
            document_no=self.document_no,
            prescription_code=self.prescription_code,
            customer=(
                CustomerDetailInput(
                    patient_name=self.customer.patient_name,
                    patient_address=self.customer.patient_address,
                )
                if self.customer is not None
                else None
            ),
            note=self.note,
        )


class SetTenantComplianceConfigRequest(BaseModel):
    """Mã cơ sở do Cục QLD cấp — cỡ tối đa 12 (Bảng 1 QĐ540 mục 22/23)."""

    ma_co_so_ban_le: str = Field(min_length=1, max_length=12)
    ma_co_so_ban_buon: str | None = Field(default=None, max_length=12)

    def to_input(self) -> SetTenantComplianceConfigInput:
        return SetTenantComplianceConfigInput(
            ma_co_so_ban_le=self.ma_co_so_ban_le,
            ma_co_so_ban_buon=self.ma_co_so_ban_buon,
        )


class CustomerDetailResponse(BaseModel):
    patient_name: str
    patient_address: str


class ControlledLedgerEntryResponse(BaseModel):
    id: UUID
    drug_id: UUID
    category: str
    direction: str
    quantity: Decimal
    lot_no: str
    expiry_date: date
    transaction_at: datetime
    source_or_destination: str
    document_no: str
    prescription_code: str | None
    customer: CustomerDetailResponse | None
    note: str | None

    @classmethod
    def of(cls, out: ControlledLedgerEntryOutput) -> ControlledLedgerEntryResponse:
        return cls(
            id=out.id,
            drug_id=out.drug_id,
            category=out.category,
            direction=out.direction,
            quantity=out.quantity,
            lot_no=out.lot_no,
            expiry_date=out.expiry_date,
            transaction_at=out.transaction_at,
            source_or_destination=out.source_or_destination,
            document_no=out.document_no,
            prescription_code=out.prescription_code,
            customer=(
                CustomerDetailResponse(
                    patient_name=out.customer.patient_name,
                    patient_address=out.customer.patient_address,
                )
                if out.customer is not None
                else None
            ),
            note=out.note,
        )


class TenantComplianceConfigResponse(BaseModel):
    tenant_id: UUID
    ma_co_so_ban_le: str
    ma_co_so_ban_buon: str | None

    @classmethod
    def of(cls, out: TenantComplianceConfigOutput) -> TenantComplianceConfigResponse:
        return cls(
            tenant_id=out.tenant_id,
            ma_co_so_ban_le=out.ma_co_so_ban_le,
            ma_co_so_ban_buon=out.ma_co_so_ban_buon,
        )


class PushSyncRequest(BaseModel):
    """Đẩy thủ công 1 bản ghi lên CSDL Dược Quốc gia.

    Luồng chính là tự động (event ``SaleCompleted`` → ``wire_compliance_sync``); endpoint này
    phục vụ việc đẩy lại thủ công khi cần (ví dụ retry sau lỗi gateway), dùng cùng
    ``client_uuid`` để idempotent với log đã có.
    """

    payload_type: SyncPayloadType
    client_uuid: str = Field(min_length=1, max_length=64)
    payload: str

    def to_input(self) -> PushSyncInput:
        return PushSyncInput(
            payload_type=self.payload_type, client_uuid=self.client_uuid, payload=self.payload
        )


class NationalSyncLogResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    payload_type: str
    payload_hash: str
    client_uuid: str
    status: str
    request_at: datetime
    response_at: datetime | None
    response_code: str | None
    response_body: str | None
    retry_count: int
    error: str | None

    @classmethod
    def of(cls, out: NationalSyncLogOutput) -> NationalSyncLogResponse:
        return cls(
            id=out.id,
            tenant_id=out.tenant_id,
            payload_type=out.payload_type,
            payload_hash=out.payload_hash,
            client_uuid=out.client_uuid,
            status=out.status,
            request_at=out.request_at,
            response_at=out.response_at,
            response_code=out.response_code,
            response_body=out.response_body,
            retry_count=out.retry_count,
            error=out.error,
        )
