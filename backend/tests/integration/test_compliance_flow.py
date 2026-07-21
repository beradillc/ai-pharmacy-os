from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import NotFoundError, ValidationError
from pharmacy_os.modules.compliance.application import (
    ComplianceService,
    CustomerDetailInput,
    RecordControlledEntryInput,
    SetTenantComplianceConfigInput,
)
from pharmacy_os.modules.compliance.domain import ControlledSubstanceCategory, LedgerDirection


def _entry(**kw: object) -> RecordControlledEntryInput:
    kw.setdefault("drug_id", uuid4())
    kw.setdefault("category", ControlledSubstanceCategory.HUONG_THAN)
    kw.setdefault("direction", LedgerDirection.XUAT)
    kw.setdefault("quantity", Decimal("2"))
    kw.setdefault("lot_no", "L20260101")
    kw.setdefault("expiry_date", date(2028, 1, 1))
    kw.setdefault("transaction_at", datetime(2026, 7, 21, 10, 0, tzinfo=UTC))
    kw.setdefault("source_or_destination", "Nhà thuốc ABC")
    kw.setdefault("document_no", "PXK-001")
    return RecordControlledEntryInput(**kw)  # type: ignore[arg-type]


async def test_record_controlled_sale_persists_and_reads_back(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    out = await compliance_service.record_controlled_entry(
        _entry(
            prescription_code="RX-001",
            customer=CustomerDetailInput(patient_name="Trần Thị B", patient_address="1 Nguyễn Huệ"),
        ),
        ctx,
    )
    assert out.category == ControlledSubstanceCategory.HUONG_THAN.value
    assert out.customer is not None
    assert out.customer.patient_name == "Trần Thị B"

    fetched = await compliance_service.get_ledger_entry(out.id, ctx)
    assert fetched.id == out.id
    assert fetched.document_no == "PXK-001"


async def test_record_controlled_sale_without_customer_rejected(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    with pytest.raises(ValidationError):
        await compliance_service.record_controlled_entry(_entry(customer=None), ctx)


async def test_record_controlled_sale_gay_nghien_without_prescription_code_rejected(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    with pytest.raises(ValidationError):
        await compliance_service.record_controlled_entry(
            _entry(
                category=ControlledSubstanceCategory.GAY_NGHIEN,
                customer=CustomerDetailInput(patient_name="A", patient_address="B"),
            ),
            ctx,
        )


async def test_record_controlled_sale_tien_chat_without_prescription_code_ok(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    out = await compliance_service.record_controlled_entry(
        _entry(
            category=ControlledSubstanceCategory.TIEN_CHAT,
            customer=CustomerDetailInput(patient_name="A", patient_address="B"),
        ),
        ctx,
    )
    assert out.prescription_code is None


async def test_record_controlled_nhap_does_not_require_customer(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    out = await compliance_service.record_controlled_entry(
        _entry(direction=LedgerDirection.NHAP, customer=None, prescription_code=None), ctx
    )
    assert out.customer is None


async def test_get_unknown_ledger_entry_raises(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    with pytest.raises(NotFoundError):
        await compliance_service.get_ledger_entry(uuid4(), ctx)


async def test_set_and_get_tenant_config_roundtrip(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    await compliance_service.set_tenant_config(
        SetTenantComplianceConfigInput(ma_co_so_ban_le="HCM-00123"), ctx
    )
    out = await compliance_service.get_tenant_config(ctx)
    assert out.ma_co_so_ban_le == "HCM-00123"
    assert out.ma_co_so_ban_buon is None


async def test_set_tenant_config_twice_upserts_not_duplicates(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    await compliance_service.set_tenant_config(
        SetTenantComplianceConfigInput(ma_co_so_ban_le="HCM-00123"), ctx
    )
    await compliance_service.set_tenant_config(
        SetTenantComplianceConfigInput(ma_co_so_ban_le="HCM-00999", ma_co_so_ban_buon="HCM-BB-01"),
        ctx,
    )
    out = await compliance_service.get_tenant_config(ctx)
    assert out.ma_co_so_ban_le == "HCM-00999"
    assert out.ma_co_so_ban_buon == "HCM-BB-01"


async def test_get_tenant_config_unset_raises(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    with pytest.raises(NotFoundError):
        await compliance_service.get_tenant_config(ctx)
