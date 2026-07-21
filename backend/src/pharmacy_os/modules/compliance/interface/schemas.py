"""Pydantic request schemas for compliance, enforcing docs/13_COMPLIANCE_SPEC.md mục C.3.

No router yet — this module's ledger data is produced by cross-module events (C.5) and
consumed by the sync gateway (C.4), not by direct user-facing CRUD endpoints at this stage.
These schemas exist as the validated request boundary for whenever that wiring lands, and
give an immediate 422 on malformed input independent of the domain-level rule in
``compliance.domain.rules`` (defense in depth — the domain rule remains the source of truth
for non-HTTP callers such as the cross-module composition root).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from pharmacy_os.modules.compliance.application.dto import (
    CustomerDetailInput,
    RecordControlledEntryInput,
    SetTenantComplianceConfigInput,
)
from pharmacy_os.modules.compliance.domain import ControlledSubstanceCategory, LedgerDirection

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
