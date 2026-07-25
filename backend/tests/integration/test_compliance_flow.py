from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.audit import AuditAction, SqlAlchemyAuditLogRepository
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import NotFoundError, ValidationError
from pharmacy_os.modules.compliance.application import (
    ComplianceService,
    CustomerDetailInput,
    RecordControlledEntryInput,
    SetTenantComplianceConfigInput,
)
from pharmacy_os.modules.compliance.domain import (
    ControlledSubstanceCategory,
    LedgerBookType,
    LedgerDirection,
)


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


# --- audit trail: the fact an inspection asks about second -------------------


async def test_recording_a_controlled_entry_leaves_an_audit_row(
    compliance_service: ComplianceService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Does not trust the call site to be wired — reads the table back."""
    out = await compliance_service.record_controlled_entry(
        _entry(
            prescription_code="RX-001",
            customer=CustomerDetailInput(patient_name="Trần Thị B", patient_address="1 Nguyễn Huệ"),
        ),
        ctx,
    )

    async with session_factory() as session:
        repo = SqlAlchemyAuditLogRepository(session)
        entries = await repo.list(
            ctx.tenant_id, action=AuditAction.CONTROLLED_LEDGER_ENTRY_RECORDED
        )
        matching = [e for e in entries if e.target_id == str(out.id)]
        assert len(matching) == 1
        # The patient's name/address must not leak into the trail.
        assert "Trần Thị B" not in str(matching[0].context)


async def test_setting_tenant_config_leaves_an_audit_row(
    compliance_service: ComplianceService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await compliance_service.set_tenant_config(
        SetTenantComplianceConfigInput(ma_co_so_ban_le="HCM-00123"), ctx
    )

    async with session_factory() as session:
        repo = SqlAlchemyAuditLogRepository(session)
        entries = await repo.list(ctx.tenant_id, action=AuditAction.TENANT_COMPLIANCE_CONFIG_SET)
        matching = [e for e in entries if e.target_id == str(ctx.tenant_id)]
        assert len(matching) == 1


async def test_ledger_book_tach_dung_2_mau_so(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    """PL VIII = GN/HT/TC (Điều 12.1.a); PL XVI = dạng phối hợp + thuốc độc (Điều 12.3)."""
    thuoc_ht, thuoc_phoi_hop, thuoc_doc = uuid4(), uuid4(), uuid4()
    await compliance_service.record_controlled_entry(
        _entry(drug_id=thuoc_ht, direction=LedgerDirection.NHAP, quantity=Decimal("100")), ctx
    )
    await compliance_service.record_controlled_entry(
        _entry(
            drug_id=thuoc_phoi_hop,
            category=ControlledSubstanceCategory.PHOI_HOP_TC,
            direction=LedgerDirection.NHAP,
            quantity=Decimal("50"),
        ),
        ctx,
    )
    await compliance_service.record_controlled_entry(
        _entry(
            drug_id=thuoc_doc,
            category=ControlledSubstanceCategory.THUOC_DOC,
            direction=LedgerDirection.NHAP,
            quantity=Decimal("7"),
        ),
        ctx,
    )

    pl_viii = await compliance_service.ledger_book_rows(
        LedgerBookType.PL_VIII, from_date=date(2026, 7, 1), to_date=date(2026, 7, 31), ctx=ctx
    )
    pl_xvi = await compliance_service.ledger_book_rows(
        LedgerBookType.PL_XVI, from_date=date(2026, 7, 1), to_date=date(2026, 7, 31), ctx=ctx
    )
    assert [r.drug_id for r in pl_viii] == [thuoc_ht]
    assert sorted(r.drug_id for r in pl_xvi) == sorted([thuoc_phoi_hop, thuoc_doc])


async def test_ledger_book_tinh_ton_luy_ke_va_loc_ky(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    drug = uuid4()
    for day, direction, qty in (
        (10, LedgerDirection.NHAP, "100"),
        (12, LedgerDirection.XUAT, "30"),
        (20, LedgerDirection.NHAP, "5"),
    ):
        await compliance_service.record_controlled_entry(
            _entry(
                drug_id=drug,
                direction=direction,
                quantity=Decimal(qty),
                transaction_at=datetime(2026, 7, day, 9, 0, tzinfo=UTC),
                customer=CustomerDetailInput(patient_name="A", patient_address="B"),
                prescription_code="RX-1",
            ),
            ctx,
        )

    ca_thang = await compliance_service.ledger_book_rows(
        LedgerBookType.PL_VIII, from_date=date(2026, 7, 1), to_date=date(2026, 7, 31), ctx=ctx
    )
    nua_dau = await compliance_service.ledger_book_rows(
        LedgerBookType.PL_VIII, from_date=date(2026, 7, 1), to_date=date(2026, 7, 15), ctx=ctx
    )
    assert [r.balance for r in ca_thang] == [Decimal("100"), Decimal("70"), Decimal("75")]
    assert len(nua_dau) == 2


async def test_ledger_book_ky_dao_nguoc_bi_tu_choi(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    with pytest.raises(ValidationError):
        await compliance_service.ledger_book_rows(
            LedgerBookType.PL_VIII, from_date=date(2026, 7, 31), to_date=date(2026, 7, 1), ctx=ctx
        )


async def test_ban_thuoc_doc_khong_can_thong_tin_khach_hang(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    """Điều 12.3 chỉ buộc sổ xuất/nhập/tồn — không có nghĩa vụ Sổ khách hàng (PL XIX)."""
    out = await compliance_service.record_controlled_entry(
        _entry(
            category=ControlledSubstanceCategory.THUOC_DOC,
            direction=LedgerDirection.XUAT,
            customer=None,
            prescription_code=None,
        ),
        ctx,
    )
    assert out.category == "THUOC_DOC"
