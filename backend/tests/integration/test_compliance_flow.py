import csv
import io
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.audit import AuditAction, AuditLogger, SqlAlchemyAuditLogRepository
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    UnauthenticatedError,
    ValidationError,
)
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.modules.compliance.application import (
    LEDGER_BOOK_CSV_HEADER,
    ComplianceService,
    CustomerDetailInput,
    RecordControlledEntryInput,
    RecordDrugReturnInput,
    ReturnedDrugItemInput,
    SetTenantComplianceConfigInput,
    SignLedgerBookInput,
)
from pharmacy_os.modules.compliance.domain import (
    ControlledSubstanceCategory,
    DrugReturnRecord,
    LedgerBookType,
    LedgerDirection,
    ReturnedDrugItem,
)
from pharmacy_os.modules.compliance.domain.ports import DrugMasterFacts, SigningReauthOutcome
from pharmacy_os.modules.compliance.infrastructure import (
    SqlAlchemyControlledLedgerRepository,
    SqlAlchemyDrugReturnRecordRepository,
    SqlAlchemyLedgerBookSignatureRepository,
    SqlAlchemyTenantComplianceConfigRepository,
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


class _FakeDrugMasterProvider:
    """Nguồn giả cho ``DrugMasterProvider`` — chỉ để test ghép tên thuốc vào báo cáo."""

    def __init__(self, facts: dict[UUID, DrugMasterFacts]) -> None:
        self._facts = facts

    async def get(self, drug_id: UUID, tenant_id: UUID) -> DrugMasterFacts | None:
        return self._facts.get(drug_id)


def _compliance_service_with_drug_master(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    drug_master: _FakeDrugMasterProvider | None = None,
) -> ComplianceService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return ComplianceService(
        uow_factory,
        lambda uow, c: SqlAlchemyControlledLedgerRepository(uow.session, c),
        lambda uow, c: SqlAlchemyTenantComplianceConfigRepository(uow.session, c),
        AuditLogger(session_factory),
        drug_master,
    )


async def test_periodic_report_tinh_dung_ton_dau_ky_va_trong_ky(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    """Mẫu số 06 (NĐ163 Điều 35.2.a) — docs/13 mục C.7."""
    drug = uuid4()
    for day, direction, qty in (
        (10, LedgerDirection.NHAP, "100"),  # trước kỳ -> tồn đầu kỳ
        (12, LedgerDirection.XUAT, "20"),  # trước kỳ -> tồn đầu kỳ
        (5, LedgerDirection.NHAP, "50"),  # trong kỳ
        (8, LedgerDirection.XUAT, "30"),  # trong kỳ
    ):
        month = 6 if day in (10, 12) else 7
        await compliance_service.record_controlled_entry(
            _entry(
                drug_id=drug,
                direction=direction,
                quantity=Decimal(qty),
                transaction_at=datetime(2026, month, day, 9, 0, tzinfo=UTC),
                customer=CustomerDetailInput(patient_name="A", patient_address="B"),
                prescription_code="RX-1",
            ),
            ctx,
        )

    rows = await compliance_service.export_periodic_report(
        from_date=date(2026, 7, 1), to_date=date(2026, 7, 31), ctx=ctx
    )
    (row,) = [r for r in rows if r.drug_id == drug]
    assert row.opening_balance == Decimal("80")  # 100 - 20
    assert row.received_in_period == Decimal("50")
    assert row.total == Decimal("130")
    assert row.issued_in_period == Decimal("30")
    assert row.closing_balance == Decimal("100")


async def test_periodic_report_khong_gom_thuoc_doc_va_danh_muc_cam(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    """Điều 35.2.b chỉ bắt bán lẻ báo cáo phóng xạ — không phải thuốc độc/danh mục cấm."""
    thuoc_ht, thuoc_doc = uuid4(), uuid4()
    await compliance_service.record_controlled_entry(
        _entry(
            drug_id=thuoc_ht,
            direction=LedgerDirection.NHAP,
            transaction_at=datetime(2026, 7, 5, 9, 0, tzinfo=UTC),
        ),
        ctx,
    )
    await compliance_service.record_controlled_entry(
        _entry(
            drug_id=thuoc_doc,
            category=ControlledSubstanceCategory.THUOC_DOC,
            direction=LedgerDirection.NHAP,
            transaction_at=datetime(2026, 7, 5, 9, 0, tzinfo=UTC),
        ),
        ctx,
    )

    rows = await compliance_service.export_periodic_report(
        from_date=date(2026, 7, 1), to_date=date(2026, 7, 31), ctx=ctx
    )
    drug_ids = {r.drug_id for r in rows}
    assert thuoc_ht in drug_ids
    assert thuoc_doc not in drug_ids


async def test_periodic_report_ky_dao_nguoc_bi_tu_choi(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    with pytest.raises(ValidationError):
        await compliance_service.export_periodic_report(
            from_date=date(2026, 7, 31), to_date=date(2026, 7, 1), ctx=ctx
        )


async def test_periodic_report_ghi_audit(
    compliance_service: ComplianceService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Bằng chứng tuân thủ: đã tạo báo cáo kỳ nào, lúc nào — docs/features/bao-cao-dinh-ky-nd163."""
    await compliance_service.export_periodic_report(
        from_date=date(2026, 7, 1), to_date=date(2026, 7, 31), ctx=ctx
    )

    async with session_factory() as session:
        repo = SqlAlchemyAuditLogRepository(session)
        entries = await repo.list(ctx.tenant_id, action=AuditAction.PERIODIC_REPORT_EXPORTED)
        matching = [e for e in entries if e.target_id == "2026-07-01_2026-07-31"]
        assert len(matching) == 1


async def test_periodic_report_dien_ten_thuoc_tu_drug_master_provider(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    drug = uuid4()
    facts = DrugMasterFacts(
        registration_no="VD-12345-26",
        base_unit="viên",
        name="Diazepam 5mg",
        form="Viên nén",
        strength="5mg",
        active_ingredients="Diazepam",
    )
    service = _compliance_service_with_drug_master(
        session_factory, event_bus, _FakeDrugMasterProvider({drug: facts})
    )
    await service.record_controlled_entry(
        _entry(
            drug_id=drug,
            direction=LedgerDirection.NHAP,
            transaction_at=datetime(2026, 7, 5, 9, 0, tzinfo=UTC),
        ),
        ctx,
    )

    (row,) = await service.export_periodic_report(
        from_date=date(2026, 7, 1), to_date=date(2026, 7, 31), ctx=ctx
    )
    assert row.drug_name == "Diazepam 5mg"
    assert row.unit == "viên"
    assert row.active_ingredients == "Diazepam"


async def test_periodic_report_thuoc_khong_tra_duoc_van_xuat_hien(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    """Không được âm thầm bỏ sót dòng khỏi báo cáo pháp lý chỉ vì catalog không có tên hiển thị
    (thuốc đã xóa khỏi catalog nhưng còn lịch sử giao dịch) — service không có drug_master.
    """
    drug = uuid4()
    await compliance_service.record_controlled_entry(
        _entry(
            drug_id=drug,
            direction=LedgerDirection.NHAP,
            transaction_at=datetime(2026, 7, 5, 9, 0, tzinfo=UTC),
        ),
        ctx,
    )

    (row,) = await compliance_service.export_periodic_report(
        from_date=date(2026, 7, 1), to_date=date(2026, 7, 31), ctx=ctx
    )
    assert row.drug_id == drug
    assert str(drug) in row.drug_name


class TestDrugReturnRecordRepository:
    """Biên bản nhận lại thuốc GN/HT/TC (docs/13 mục C.6) — repository add/get roundtrip."""

    def _record(self, ctx: RequestContext) -> DrugReturnRecord:
        return DrugReturnRecord(
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            returner_name="Nguyễn Văn A",
            returner_address="12 Lê Lợi, Q1, HCM",
            returner_id_number="079123456789",
            returner_id_issuer="Cục Cảnh sát QLHC về TTXH",
            returner_id_issued_at=date(2021, 5, 1),
            returner_is_patient=True,
            receiving_pharmacist_name="DS. Trần Thị B",
            items=[
                ReturnedDrugItem(
                    description="Diazepam 5mg, viên nén, hộp 2 vỉ x 10 viên",
                    unit="viên",
                    quantity=Decimal("3"),
                    lot_no="L20260101",
                    expiry_date=date(2028, 1, 1),
                    condition_note="Còn nguyên vỉ",
                    reason="Người bệnh không dùng hết",
                ),
                ReturnedDrugItem(
                    description="Tramadol 37.5mg",
                    unit="viên",
                    quantity=Decimal("5"),
                    lot_no="L20260202",
                    expiry_date=date(2027, 6, 1),
                    condition_note="Vỉ đã bóc, còn 5 viên",
                    reason="Người bệnh tử vong",
                ),
            ],
            handover_at=datetime(2026, 7, 25, 14, 30, tzinfo=UTC),
            handover_location="Nhà thuốc ABC, 12 Lê Lợi, Q1, HCM",
        )

    async def test_add_va_get_giu_nguyen_du_lieu_ke_ca_nhieu_dong_thuoc(
        self, session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
    ) -> None:
        ctx = RequestContext(
            tenant_id=uuid4(),
            branch_id=uuid4(),
            user_id=uuid4(),
            permissions=frozenset({"compliance.ledger.write", "compliance.ledger.read"}),
        )
        record = self._record(ctx)

        async with SqlAlchemyUnitOfWork(session_factory, event_bus) as uow:
            repo = SqlAlchemyDrugReturnRecordRepository(uow.session, ctx)
            await repo.add(record)
            await uow.commit()

        async with SqlAlchemyUnitOfWork(session_factory, event_bus) as uow:
            repo = SqlAlchemyDrugReturnRecordRepository(uow.session, ctx)
            fetched = await repo.get(record.id)

        assert fetched is not None
        assert fetched.returner_name == "Nguyễn Văn A"
        assert fetched.returner_id_number == "079123456789"
        assert len(fetched.items) == 2
        assert {i.description for i in fetched.items} == {
            "Diazepam 5mg, viên nén, hộp 2 vỉ x 10 viên",
            "Tramadol 37.5mg",
        }
        assert fetched.items[0].quantity in (Decimal("3"), Decimal("5"))

    async def test_get_tra_ve_none_ngoai_tenant(
        self, session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
    ) -> None:
        ctx = RequestContext(
            tenant_id=uuid4(),
            branch_id=uuid4(),
            user_id=uuid4(),
            permissions=frozenset({"compliance.ledger.write"}),
        )
        record = self._record(ctx)
        async with SqlAlchemyUnitOfWork(session_factory, event_bus) as uow:
            repo = SqlAlchemyDrugReturnRecordRepository(uow.session, ctx)
            await repo.add(record)
            await uow.commit()

        other_ctx = RequestContext(
            tenant_id=uuid4(), branch_id=uuid4(), user_id=uuid4(), permissions=frozenset()
        )
        async with SqlAlchemyUnitOfWork(session_factory, event_bus) as uow:
            repo = SqlAlchemyDrugReturnRecordRepository(uow.session, other_ctx)
            fetched = await repo.get(record.id)
        assert fetched is None


def _drug_return_input(**kw: object) -> RecordDrugReturnInput:
    base: dict[str, object] = {
        "returner_name": "Nguyễn Văn A",
        "returner_address": "12 Lê Lợi, Q1, HCM",
        "returner_id_number": "079123456789",
        "returner_id_issuer": "Cục Cảnh sát QLHC về TTXH",
        "returner_id_issued_at": date(2021, 5, 1),
        "returner_is_patient": True,
        "receiving_pharmacist_name": "DS. Trần Thị B",
        "items": [
            ReturnedDrugItemInput(
                description="Diazepam 5mg",
                unit="viên",
                quantity=Decimal("3"),
                lot_no="L20260101",
                expiry_date=date(2028, 1, 1),
                condition_note="Còn nguyên vỉ",
                reason="Không dùng hết",
            )
        ],
        "handover_at": datetime(2026, 7, 25, 14, 30, tzinfo=UTC),
        "handover_location": "Nhà thuốc ABC",
    }
    base.update(kw)
    return RecordDrugReturnInput(**base)  # type: ignore[arg-type]


async def test_record_drug_return_persists_and_reads_back(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    out = await compliance_service.record_drug_return(_drug_return_input(), ctx)
    assert out.returner_name == "Nguyễn Văn A"
    assert len(out.items) == 1

    fetched = await compliance_service.get_drug_return(out.id, ctx)
    assert fetched.id == out.id
    assert fetched.returner_id_number == "079123456789"


async def test_get_unknown_drug_return_raises(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    with pytest.raises(NotFoundError):
        await compliance_service.get_drug_return(uuid4(), ctx)


async def test_recording_a_drug_return_leaves_an_audit_row_without_id_number(
    compliance_service: ComplianceService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    out = await compliance_service.record_drug_return(_drug_return_input(), ctx)

    async with session_factory() as session:
        repo = SqlAlchemyAuditLogRepository(session)
        entries = await repo.list(ctx.tenant_id, action=AuditAction.DRUG_RETURN_RECORDED)
        matching = [e for e in entries if e.target_id == str(out.id)]
        assert len(matching) == 1
        assert "079123456789" not in str(matching[0].context)


async def test_export_daily_closure_tinh_dung_hash_va_so_dong(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    """docs/13 mục C.5 — kết xuất cuối ngày, điều kiện (a) Điều 15.1 (toàn vẹn, có hash)."""
    drug = uuid4()
    await compliance_service.record_controlled_entry(
        _entry(
            drug_id=drug,
            direction=LedgerDirection.NHAP,
            quantity=Decimal("10"),
            transaction_at=datetime(2026, 7, 25, 9, 0, tzinfo=UTC),
        ),
        ctx,
    )
    # Giao dịch khác ngày — không được lẫn vào kết xuất của 25/7.
    await compliance_service.record_controlled_entry(
        _entry(
            drug_id=drug,
            direction=LedgerDirection.NHAP,
            quantity=Decimal("99"),
            transaction_at=datetime(2026, 7, 26, 9, 0, tzinfo=UTC),
        ),
        ctx,
    )

    export = await compliance_service.export_daily_closure(
        LedgerBookType.PL_VIII, day=date(2026, 7, 25), ctx=ctx
    )
    assert export.row_count == 1
    assert export.day == date(2026, 7, 25)
    assert len(export.content_sha256) == 64  # hex SHA-256
    # Đọc CSV theo cột, không tìm chuỗi con: cột cuối là ``drug_id`` (UUID ngẫu nhiên mỗi
    # lần chạy), nên `"99" not in content` có lúc trúng ngay trong UUID và đỏ oan —
    # đã bắt được thật (~8% số lần chạy) khi rà nợ retry DAV, 2026-07-25.
    header, *data_rows = list(csv.reader(io.StringIO(export.content)))
    assert tuple(header) == LEDGER_BOOK_CSV_HEADER
    assert len(data_rows) == 1
    assert data_rows[0][3] == "10"  # so_luong_nhap của giao dịch 25/7
    assert "99" not in data_rows[0][3:6]  # không lẫn số lượng của giao dịch 26/7


async def test_export_daily_closure_ngay_trong_khong_co_giao_dich_van_ra_header(
    compliance_service: ComplianceService, ctx: RequestContext
) -> None:
    export = await compliance_service.export_daily_closure(
        LedgerBookType.PL_VIII, day=date(2026, 1, 1), ctx=ctx
    )
    assert export.row_count == 0
    assert export.content_sha256  # vẫn có hash — chuỗi rỗng cũng băm được, không phải lỗi


async def test_export_daily_closure_leaves_an_audit_row_with_hash(
    compliance_service: ComplianceService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    export = await compliance_service.export_daily_closure(
        LedgerBookType.PL_VIII, day=date(2026, 7, 25), ctx=ctx
    )

    async with session_factory() as session:
        repo = SqlAlchemyAuditLogRepository(session)
        entries = await repo.list(ctx.tenant_id, action=AuditAction.LEDGER_DAILY_CLOSURE_EXPORTED)
        matching = [e for e in entries if e.target_id == "PL_VIII_2026-07-25"]
        assert len(matching) == 1
        assert matching[0].context.get("content_sha256") == export.content_sha256


# --- bước 6/6 TT18: ký xác nhận điện tử (hướng A, docs/13 mục C.5) ---------


class _FakeReauthProvider:
    """Xác minh giả cho ``SigningReauthProvider`` — 1 mật khẩu đúng cố định, 2FA tuỳ chọn.

    Mặc định ``required_code=None`` = tài khoản chưa bật 2FA, nên các test cũ (chỉ mật
    khẩu) giữ nguyên hành vi — chính là tính tương thích ngược mà thiết kế cam kết.
    """

    def __init__(
        self, correct_password: str = "MatKhauDung2026", required_code: str | None = None
    ) -> None:
        self.correct_password = correct_password
        self.required_code = required_code

    async def verify(
        self, ctx: RequestContext, plain_password: str, totp_code: str | None
    ) -> SigningReauthOutcome:
        if plain_password != self.correct_password:
            return SigningReauthOutcome.BAD_PASSWORD
        if self.required_code is None:
            return SigningReauthOutcome.OK
        if totp_code is None:
            return SigningReauthOutcome.CODE_REQUIRED
        if totp_code != self.required_code:
            return SigningReauthOutcome.BAD_CODE
        return SigningReauthOutcome.OK


def _compliance_service_with_signing(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    reauth: _FakeReauthProvider | None = None,
) -> ComplianceService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return ComplianceService(
        uow_factory,
        lambda uow, c: SqlAlchemyControlledLedgerRepository(uow.session, c),
        lambda uow, c: SqlAlchemyTenantComplianceConfigRepository(uow.session, c),
        AuditLogger(session_factory),
        signature_repo_factory=lambda uow, c: SqlAlchemyLedgerBookSignatureRepository(
            uow.session, c
        ),
        reauth=reauth if reauth is not None else _FakeReauthProvider(),
    )


def _sign_input(**kw: object) -> SignLedgerBookInput:
    kw.setdefault("book_type", LedgerBookType.PL_VIII)
    kw.setdefault("book_date", date(2026, 7, 25))
    kw.setdefault("current_password", "MatKhauDung2026")
    return SignLedgerBookInput(**kw)  # type: ignore[arg-type]


async def test_sign_daily_closure_requires_the_permission(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> None:
    service = _compliance_service_with_signing(session_factory, event_bus)
    ctx = RequestContext(
        tenant_id=uuid4(), branch_id=uuid4(), user_id=uuid4(), permissions=frozenset()
    )
    with pytest.raises(PermissionDeniedError):
        await service.sign_daily_closure(_sign_input(), ctx)


async def test_sign_daily_closure_rejects_the_wrong_password(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    service = _compliance_service_with_signing(session_factory, event_bus)
    with pytest.raises(UnauthenticatedError):
        await service.sign_daily_closure(_sign_input(current_password="SaiRoi"), ctx)


# --- step-up: ký sổ đòi CẢ HAI yếu tố khi tài khoản đã bật 2FA (Sprint 8) ----
#
# Vì sao mật khẩu một mình là không đủ ở đây: ký sổ là hành vi pháp lý KHÔNG ĐẢO
# NGƯỢC ĐƯỢC (TT18 Điều 15.1.d — ký xong là chốt sổ, không ghi thêm, không ký lại).
# Một mật khẩu lộ mà đủ để ký thì chữ ký đó vô giá trị về mặt chứng cứ.


async def test_signing_needs_the_code_when_two_factor_is_on(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    """Mật khẩu đúng nhưng thiếu mã ⇒ từ chối, nêu rõ là thiếu mã."""
    service = _compliance_service_with_signing(
        session_factory, event_bus, reauth=_FakeReauthProvider(required_code="123456")
    )
    with pytest.raises(UnauthenticatedError, match="xác thực hai lớp"):
        await service.sign_daily_closure(_sign_input(), ctx)


async def test_signing_rejects_a_wrong_code(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    service = _compliance_service_with_signing(
        session_factory, event_bus, reauth=_FakeReauthProvider(required_code="123456")
    )
    with pytest.raises(UnauthenticatedError, match="Mã xác thực"):
        await service.sign_daily_closure(_sign_input(totp_code="000000"), ctx)


async def test_signing_succeeds_with_password_and_code(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    service = _compliance_service_with_signing(
        session_factory, event_bus, reauth=_FakeReauthProvider(required_code="123456")
    )
    out = await service.sign_daily_closure(_sign_input(totp_code="123456"), ctx)
    assert out.content_sha256


async def test_a_wrong_password_is_refused_even_with_the_right_code(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    """Yếu tố thứ hai là THÊM, không phải THAY — không cái nào bỏ qua được cái kia."""
    service = _compliance_service_with_signing(
        session_factory, event_bus, reauth=_FakeReauthProvider(required_code="123456")
    )
    with pytest.raises(UnauthenticatedError, match="Mật khẩu"):
        await service.sign_daily_closure(
            _sign_input(current_password="SaiRoi", totp_code="123456"), ctx
        )


async def test_signing_is_blocked_until_enrolment_when_enforced(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    """403 chứ không phải 401: danh tính hợp lệ, chỉ là chưa đủ điều kiện để ký.

    Đây là điểm DUY NHẤT bị chặn cứng khi bật cưỡng chế — đăng nhập và mọi việc khác
    vẫn chạy bình thường ("nhắc rộng, chặn hẹp").
    """

    class _EnforcedNotEnrolled(_FakeReauthProvider):
        async def verify(
            self, ctx: RequestContext, plain_password: str, totp_code: str | None
        ) -> SigningReauthOutcome:
            return SigningReauthOutcome.ENROLLMENT_REQUIRED

    service = _compliance_service_with_signing(
        session_factory, event_bus, reauth=_EnforcedNotEnrolled()
    )
    with pytest.raises(PermissionDeniedError, match="đăng ký xác thực hai lớp"):
        await service.sign_daily_closure(_sign_input(), ctx)


async def test_signing_without_two_factor_still_works_backward_compatible(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    """Người chưa bật 2FA, hệ thống chưa cưỡng chế ⇒ hành vi y hệt trước Sprint 8."""
    service = _compliance_service_with_signing(session_factory, event_bus)
    out = await service.sign_daily_closure(_sign_input(), ctx)
    assert out.content_sha256


async def test_sign_daily_closure_records_hash_and_chains_to_the_previous_signature(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    service = _compliance_service_with_signing(session_factory, event_bus)
    await service.record_controlled_entry(
        _entry(
            transaction_at=datetime(2026, 7, 24, 9, 0, tzinfo=UTC),
            customer=CustomerDetailInput(patient_name="A", patient_address="B"),
            prescription_code="RX-SIGN-01",
        ),
        ctx,
    )
    first = await service.sign_daily_closure(_sign_input(book_date=date(2026, 7, 24)), ctx)
    assert first.prev_hash is None
    assert len(first.content_sha256) == 64
    assert first.signed_by_user_id == ctx.user_id

    second = await service.sign_daily_closure(_sign_input(book_date=date(2026, 7, 25)), ctx)
    assert second.prev_hash == first.content_sha256


async def test_sign_daily_closure_rejects_signing_the_same_day_twice(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    service = _compliance_service_with_signing(session_factory, event_bus)
    await service.sign_daily_closure(_sign_input(), ctx)
    with pytest.raises(ConflictError):
        await service.sign_daily_closure(_sign_input(), ctx)


async def test_sign_daily_closure_leaves_an_audit_row_with_hash(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    service = _compliance_service_with_signing(session_factory, event_bus)
    signed = await service.sign_daily_closure(_sign_input(), ctx)

    async with session_factory() as session:
        repo = SqlAlchemyAuditLogRepository(session)
        entries = await repo.list(ctx.tenant_id, action=AuditAction.LEDGER_BOOK_SIGNED)
        matching = [e for e in entries if e.target_id == "PL_VIII_2026-07-25"]
        assert len(matching) == 1
        assert matching[0].context.get("content_sha256") == signed.content_sha256


async def test_record_controlled_entry_is_blocked_after_the_day_is_signed(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    """docs/13 mục C.5 — hệ quả "ký xong là chốt sổ": không ghi thêm được vào ngày đã ký."""
    service = _compliance_service_with_signing(session_factory, event_bus)
    await service.sign_daily_closure(_sign_input(), ctx)

    with pytest.raises(ConflictError):
        await service.record_controlled_entry(
            _entry(
                transaction_at=datetime(2026, 7, 25, 15, 0, tzinfo=UTC),
                customer=CustomerDetailInput(patient_name="A", patient_address="B"),
                prescription_code="RX-SIGN-02",
            ),
            ctx,
        )
