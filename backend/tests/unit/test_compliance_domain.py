"""Domain tests for module `compliance` — see docs/13_COMPLIANCE_SPEC.md."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from pharmacy_os.modules.compliance.domain import (
    ComplianceError,
    ControlledLedgerEntry,
    ControlledSubstanceCategory,
    CustomerDetail,
    EtcPrescriptionPolicy,
    LedgerDirection,
    MissingControlledCustomerDetailError,
    MissingControlledPrescriptionCodeError,
    MissingEtcPrescriptionFieldsError,
    NationalDrugRecord,
    NotControlledSubstanceError,
    TenantComplianceConfig,
    to_qld_code,
    to_qld_date,
    to_qld_datetime,
    validate_controlled_sale,
    validate_etc_sale,
)

# --- A. Converter helpers (docs/13 mục A) ---------------------------------


def test_to_qld_date_formats_yyyymmdd() -> None:
    assert to_qld_date(date(2018, 12, 15)) == 20181215


def test_to_qld_datetime_formats_yyyymmddhhmm() -> None:
    assert to_qld_datetime(datetime(2018, 8, 8, 10, 30, tzinfo=UTC)) == 201808081030


def test_to_qld_code_matches_legal_example() -> None:
    """VD gốc QĐ540 Bảng 1 mục 1: bỏ dấu, bỏ khoảng trắng/gạch ngang, GIỮ chữ thường."""
    assert to_qld_code("VN-12345-18-lọ 200 viên") == "VN1234518lo200vien"


def test_to_qld_code_handles_dd_explicitly() -> None:
    assert to_qld_code("đường Đinh") == "duongDinh"


def test_to_qld_code_no_diacritics_or_separators_left() -> None:
    coded = to_qld_code("VD-12345-17-hộp 10 vỉ x 10 viên")
    assert "-" not in coded
    assert " " not in coded


# --- B. NationalDrugRecord — 23 field Bảng 1 (docs/13 mục B) --------------


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


def test_national_drug_record_holds_23_fields() -> None:
    rec = _record()
    assert rec.so_dang_ky == "VD-12345-17"
    assert rec.so_luong_ton == Decimal("600")
    assert rec.han_dung == date(2028, 1, 1)


def test_national_drug_record_coerces_decimal_quantities() -> None:
    rec = _record(gia_ban_le="1500", so_luong_nhap="1000", so_luong_ban="400", so_luong_ton="600")
    assert rec.gia_ban_le == Decimal("1500")
    assert isinstance(rec.so_luong_ton, Decimal)


def test_national_drug_record_is_immutable() -> None:
    rec = _record()
    with pytest.raises(AttributeError):
        rec.ten_thuoc = "khác"  # type: ignore[misc]


# --- C.1 Phân loại — ControlledSubstanceCategory (docs/13 mục C.1) --------


def test_controlled_substance_category_has_7_values() -> None:
    assert {c.value for c in ControlledSubstanceCategory} == {
        "GAY_NGHIEN",
        "HUONG_THAN",
        "TIEN_CHAT",
        "PHOI_HOP_GN",
        "PHOI_HOP_HT",
        "PHOI_HOP_TC",
        "NONE",
    }


# --- CustomerDetail (Phụ lục XXI, docs/13 mục C.3 rule 2) -----------------


def test_customer_detail_only_name_and_address() -> None:
    detail = CustomerDetail(patient_name="Nguyễn Văn A", patient_address="12 Lê Lợi, Q1, HCM")
    assert detail.patient_name == "Nguyễn Văn A"
    assert not hasattr(detail, "patient_id")


def test_customer_detail_rejects_blank_name() -> None:
    with pytest.raises(ValueError, match="Tên khách hàng"):
        CustomerDetail(patient_name="  ", patient_address="12 Lê Lợi")


def test_customer_detail_rejects_blank_address() -> None:
    with pytest.raises(ValueError, match="Địa chỉ"):
        CustomerDetail(patient_name="Nguyễn Văn A", patient_address="")


# --- ControlledLedgerEntry (docs/13 mục C.2.1) ----------------------------


def _ledger_entry(**overrides: object) -> ControlledLedgerEntry:
    base: dict[str, object] = {
        "tenant_id": uuid4(),
        "branch_id": uuid4(),
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
    return ControlledLedgerEntry(**base)  # type: ignore[arg-type]


def test_ledger_entry_rejects_none_category() -> None:
    with pytest.raises(NotControlledSubstanceError):
        _ledger_entry(category=ControlledSubstanceCategory.NONE)


def test_ledger_entry_rejects_non_positive_quantity() -> None:
    with pytest.raises(ValueError):
        _ledger_entry(quantity=Decimal("0"))


def test_ledger_entry_accepts_optional_customer_and_prescription() -> None:
    entry = _ledger_entry(
        prescription_code="RX-001",
        customer=CustomerDetail(patient_name="Trần Thị B", patient_address="1 Nguyễn Huệ"),
    )
    assert entry.customer is not None
    assert entry.customer.patient_name == "Trần Thị B"
    assert entry.prescription_code == "RX-001"


# --- C.3 rule 1 — ETC, feature-flag TẮT mặc định --------------------------


def test_etc_policy_disabled_by_default() -> None:
    policy = EtcPrescriptionPolicy()
    assert policy.require_etc_prescription_fields is False


def test_validate_etc_sale_noop_when_disabled() -> None:
    policy = EtcPrescriptionPolicy()  # default off
    validate_etc_sale(policy, prescription_code=None, patient_name=None, doctor_name=None)


def test_validate_etc_sale_enforces_when_enabled() -> None:
    policy = EtcPrescriptionPolicy(require_etc_prescription_fields=True)
    with pytest.raises(MissingEtcPrescriptionFieldsError):
        validate_etc_sale(policy, prescription_code=None, patient_name="A", doctor_name="BS. B")


def test_validate_etc_sale_passes_when_enabled_and_complete() -> None:
    policy = EtcPrescriptionPolicy(require_etc_prescription_fields=True)
    validate_etc_sale(policy, prescription_code="RX-1", patient_name="A", doctor_name="BS. B")


# --- C.3 rule 2 — GN/HT/TC controlled sale validation ---------------------


def test_validate_controlled_sale_noop_for_none_category() -> None:
    validate_controlled_sale(
        ControlledSubstanceCategory.NONE, prescription_code=None, customer=None
    )


def test_validate_controlled_sale_requires_customer_detail() -> None:
    with pytest.raises(MissingControlledCustomerDetailError):
        validate_controlled_sale(
            ControlledSubstanceCategory.TIEN_CHAT, prescription_code=None, customer=None
        )


def test_validate_controlled_sale_tien_chat_does_not_require_prescription_code() -> None:
    customer = CustomerDetail(patient_name="A", patient_address="B")
    validate_controlled_sale(
        ControlledSubstanceCategory.TIEN_CHAT, prescription_code=None, customer=customer
    )


def test_validate_controlled_sale_gay_nghien_requires_prescription_code() -> None:
    customer = CustomerDetail(patient_name="A", patient_address="B")
    with pytest.raises(MissingControlledPrescriptionCodeError):
        validate_controlled_sale(
            ControlledSubstanceCategory.GAY_NGHIEN, prescription_code=None, customer=customer
        )


def test_validate_controlled_sale_huong_than_requires_prescription_code() -> None:
    customer = CustomerDetail(patient_name="A", patient_address="B")
    with pytest.raises(MissingControlledPrescriptionCodeError):
        validate_controlled_sale(
            ControlledSubstanceCategory.HUONG_THAN, prescription_code=None, customer=customer
        )


def test_validate_controlled_sale_passes_gay_nghien_with_prescription_code() -> None:
    customer = CustomerDetail(patient_name="A", patient_address="B")
    validate_controlled_sale(
        ControlledSubstanceCategory.GAY_NGHIEN,
        prescription_code="RX-1",
        customer=customer,
    )


def test_compliance_errors_share_base_class() -> None:
    assert issubclass(MissingControlledCustomerDetailError, ComplianceError)
    assert issubclass(MissingControlledPrescriptionCodeError, ComplianceError)
    assert issubclass(MissingEtcPrescriptionFieldsError, ComplianceError)
    assert issubclass(NotControlledSubstanceError, ComplianceError)


# --- TenantComplianceConfig (docs/13 mục F) --------------------------------


def test_tenant_compliance_config_ma_co_so_ban_buon_optional() -> None:
    config = TenantComplianceConfig(tenant_id=uuid4(), ma_co_so_ban_le="HCM-00123")
    assert config.ma_co_so_ban_buon is None


def test_tenant_compliance_config_rejects_blank_ma_co_so_ban_le() -> None:
    with pytest.raises(ValueError, match="ma_co_so_ban_le"):
        TenantComplianceConfig(tenant_id=uuid4(), ma_co_so_ban_le="  ")
