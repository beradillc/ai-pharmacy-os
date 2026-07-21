"""Interface-layer tests: Pydantic schemas + export mapper for module `compliance`.

See docs/13_COMPLIANCE_SPEC.md mục A (converter helpers), mục B (23 trường Bảng 1) and
mục C.3 (validation rules).
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from pharmacy_os.modules.compliance.domain import (
    ControlledSubstanceCategory,
    LedgerDirection,
    NationalDrugRecord,
)
from pharmacy_os.modules.compliance.interface.export import (
    NationalDrugRecordExport,
    to_national_drug_record_export,
)
from pharmacy_os.modules.compliance.interface.schemas import (
    CustomerDetailRequest,
    RecordControlledEntryRequest,
    SetTenantComplianceConfigRequest,
)

# --- RecordControlledEntryRequest — field_validator cho rule C.3 ----------


def _payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "drug_id": uuid4(),
        "category": ControlledSubstanceCategory.HUONG_THAN,
        "direction": LedgerDirection.XUAT,
        "quantity": Decimal("2"),
        "lot_no": "L20260101",
        "expiry_date": date(2028, 1, 1),
        "transaction_at": datetime(2026, 7, 21, 10, 0, tzinfo=UTC),
        "source_or_destination": "Nhà thuốc ABC",
        "document_no": "PXK-001",
    }
    base.update(overrides)
    return base


def test_xuat_controlled_without_customer_rejected() -> None:
    with pytest.raises(ValidationError):
        RecordControlledEntryRequest(**_payload(customer=None))


def test_xuat_gay_nghien_without_prescription_code_rejected() -> None:
    with pytest.raises(ValidationError):
        RecordControlledEntryRequest(
            **_payload(
                category=ControlledSubstanceCategory.GAY_NGHIEN,
                customer=CustomerDetailRequest(patient_name="A", patient_address="B"),
            )
        )


def test_xuat_tien_chat_without_prescription_code_ok() -> None:
    req = RecordControlledEntryRequest(
        **_payload(
            category=ControlledSubstanceCategory.TIEN_CHAT,
            customer=CustomerDetailRequest(patient_name="A", patient_address="B"),
        )
    )
    assert req.prescription_code is None


def test_xuat_gay_nghien_with_prescription_code_ok() -> None:
    req = RecordControlledEntryRequest(
        **_payload(
            category=ControlledSubstanceCategory.GAY_NGHIEN,
            prescription_code="RX-1",
            customer=CustomerDetailRequest(patient_name="A", patient_address="B"),
        )
    )
    assert req.prescription_code == "RX-1"


def test_nhap_direction_skips_customer_rule() -> None:
    req = RecordControlledEntryRequest(
        **_payload(
            direction=LedgerDirection.NHAP,
            category=ControlledSubstanceCategory.GAY_NGHIEN,
            customer=None,
            prescription_code=None,
        )
    )
    assert req.customer is None


def test_none_category_skips_rule_entirely() -> None:
    req = RecordControlledEntryRequest(
        **_payload(category=ControlledSubstanceCategory.NONE, customer=None)
    )
    assert req.customer is None


def test_to_input_conversion() -> None:
    req = RecordControlledEntryRequest(
        **_payload(
            category=ControlledSubstanceCategory.TIEN_CHAT,
            customer=CustomerDetailRequest(patient_name="A", patient_address="B"),
        )
    )
    data = req.to_input()
    assert data.category is ControlledSubstanceCategory.TIEN_CHAT
    assert data.customer is not None
    assert data.customer.patient_name == "A"


# --- SetTenantComplianceConfigRequest — cỡ 12 theo Bảng 1 mục 22/23 -------


def test_tenant_config_ma_co_so_ban_le_max_length_12() -> None:
    with pytest.raises(ValidationError):
        SetTenantComplianceConfigRequest(ma_co_so_ban_le="X" * 13)


def test_tenant_config_ma_co_so_ban_buon_optional() -> None:
    req = SetTenantComplianceConfigRequest(ma_co_so_ban_le="HCM-00123")
    assert req.ma_co_so_ban_buon is None


# --- Export mapper (docs/13 mục A + B) -------------------------------------


def _record(**overrides: object) -> NationalDrugRecord:
    base: dict[str, object] = {
        "ma_thuoc": "VD-12345-17-lọ 200 viên",
        "ten_thuoc": "Paracetamol 500mg",
        "so_dang_ky": "VD-12345-17",
        "ten_hoat_chat": "Paracetamol",
        "nong_do_ham_luong": "500mg",
        "nha_san_xuat": "Công ty Dược ABC",
        "nuoc_san_xuat": "Việt Nam",
        "nha_nhap_khau": "Công ty XNK XYZ",
        "quy_cach_dong_goi": "Lọ 200 viên",
        "dang_bao_che": "Viên nén",
        "don_vi_dong_goi_nn": "viên",
        "gia_ban_le": Decimal("1500"),
        "so_lo": "L20260101",
        "han_dung": date(2028, 1, 1),
        "so_luong_nhap": Decimal("1000"),
        "so_luong_ban": Decimal("400"),
        "so_luong_ton": Decimal("600"),
        "don_vi_bthuoc_cho_csbl": "Công ty Dược Phẩm Trung Ương",
        "so_hoa_don_mthuoc": "HD00123",
        "ngay_nhap": datetime(2026, 1, 5, 9, 0, tzinfo=UTC),
        "ngay_ban": datetime(2026, 3, 1, 14, 30, tzinfo=UTC),
        "ma_co_so_ban_le": "HCM-00123",
        "ma_co_so_ban_buon": "HCM-BB-045",
    }
    base.update(overrides)
    return NationalDrugRecord(**base)  # type: ignore[arg-type]


def test_export_mapper_encodes_ma_thuoc_via_to_qld_code() -> None:
    export = to_national_drug_record_export(_record())
    assert export.ma_thuoc == "VD1234517lo200vien"


def test_export_mapper_encodes_dates_via_converters() -> None:
    export = to_national_drug_record_export(_record())
    assert export.han_dung == 20280101
    assert export.ngay_nhap == 202601050900
    assert export.ngay_ban == 202603011430


def test_export_mapper_passes_through_untouched_fields() -> None:
    export = to_national_drug_record_export(_record())
    assert export.so_dang_ky == "VD-12345-17"
    assert export.so_luong_ton == Decimal("600")
    assert isinstance(export, NationalDrugRecordExport)


def test_export_schema_enforces_max_length_from_bang_1() -> None:
    with pytest.raises(ValidationError):
        NationalDrugRecordExport(
            ma_thuoc="X" * 51,  # cỡ tối đa 50 (Bảng 1 mục 1)
            ten_thuoc="Paracetamol",
            so_dang_ky="VD-12345-17",
            ten_hoat_chat="Paracetamol",
            nong_do_ham_luong="500mg",
            nha_san_xuat="ABC",
            nuoc_san_xuat="Việt Nam",
            nha_nhap_khau="XYZ",
            quy_cach_dong_goi="Lọ",
            dang_bao_che="Viên",
            don_vi_dong_goi_nn="viên",
            gia_ban_le=Decimal("1500"),
            so_lo="L1",
            han_dung=20280101,
            so_luong_nhap=Decimal("10"),
            so_luong_ban=Decimal("5"),
            so_luong_ton=Decimal("5"),
            don_vi_bthuoc_cho_csbl="Cty",
            so_hoa_don_mthuoc="HD1",
            ngay_nhap=202601050900,
            ngay_ban=202603011430,
            ma_co_so_ban_le="HCM-1",
            ma_co_so_ban_buon="HCM-BB-1",
        )
