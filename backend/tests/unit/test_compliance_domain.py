"""Domain tests for module `compliance` — see docs/13_COMPLIANCE_SPEC.md."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from pharmacy_os.modules.compliance.domain import (
    ComplianceError,
    ControlledLedgerEntry,
    ControlledSubstance,
    ControlledSubstanceAppendix,
    ControlledSubstanceCategory,
    CustomerDetail,
    DrugReturnRecord,
    EtcPrescriptionPolicy,
    LedgerBookSignature,
    LedgerBookType,
    LedgerDirection,
    LedgerPeriodAggregate,
    MissingControlledCustomerDetailError,
    MissingControlledPrescriptionCodeError,
    MissingEtcPrescriptionFieldsError,
    NationalDrugRecord,
    NotControlledSubstanceError,
    ReturnedDrugItem,
    TenantComplianceConfig,
    book_type_for,
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


def test_controlled_substance_category_has_9_values() -> None:
    """7 → 9 giá trị (2026-07-25): TT18 Điều 12.3 kéo thuốc độc + danh mục cấm vào

    nghĩa vụ sổ sách của cơ sở BÁN LẺ; TT20/2017 không có nên bản cũ đã loại 2 nhóm này.
    """
    assert {c.value for c in ControlledSubstanceCategory} == {
        "GAY_NGHIEN",
        "HUONG_THAN",
        "TIEN_CHAT",
        "PHOI_HOP_GN",
        "PHOI_HOP_HT",
        "PHOI_HOP_TC",
        "THUOC_DOC",
        "DANH_MUC_CAM",
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


class TestControlledSubstance:
    """Danh mục dược chất kiểm soát đặc biệt — TT 18/2026 Phụ lục I/II/III + IV/V/VI."""

    def test_category_suy_ra_tu_phu_luc(self) -> None:
        gn = ControlledSubstance(
            name_intl="MORPHINE",
            scientific_name="(5α,6α)-7,8-didehydro-4,5-epoxy-17-methylmorphinan-3,6-diol",
            appendix=ControlledSubstanceAppendix.PL_I,
            limit_concentration_pct=Decimal("0.2"),
        )
        ht = ControlledSubstance(
            name_intl="DIAZEPAM",
            scientific_name="7-chloro-1,3-dihydro-1-methyl-5-phenyl-2H-1,4-benzodiazepin-2-one",
            appendix=ControlledSubstanceAppendix.PL_II,
            limit_per_unit_mg=Decimal("5"),
        )
        tc = ControlledSubstance(
            name_intl="PSEUDOEPHEDRINE",
            scientific_name="[S-(R*,R*)]--[1-(methylamino)ethyl]-Benzenemethanol",
            appendix=ControlledSubstanceAppendix.PL_III,
            limit_per_unit_mg=Decimal("120"),
            limit_concentration_pct=Decimal("0.5"),
        )
        assert gn.category is ControlledSubstanceCategory.GAY_NGHIEN
        assert ht.category is ControlledSubstanceCategory.HUONG_THAN
        assert tc.category is ControlledSubstanceCategory.TIEN_CHAT

    def test_khong_co_gioi_han_van_hop_le(self) -> None:
        """Phần lớn chất trong PL I/II/III không có ngưỡng ở PL IV/V/VI — 60/122 chất."""
        chat = ControlledSubstance(
            name_intl="FENTANYL",
            scientific_name="1-phenethyl- 4- N-propionylanilinopiperidine",
            appendix=ControlledSubstanceAppendix.PL_I,
        )
        assert chat.limit_per_unit_mg is None
        assert chat.limit_concentration_pct is None

    def test_gioi_han_dang_chuoi_duoc_ep_ve_decimal(self) -> None:
        chat = ControlledSubstance(
            name_intl="TRAMADOL",
            scientific_name="(±)-Trans-2-Dimethylaminomethyl-1-(3-methoxyphenyl)cyclohexan-1-ol",
            appendix=ControlledSubstanceAppendix.PL_I,
            limit_per_unit_mg="37.5",  # type: ignore[arg-type]
        )
        assert chat.limit_per_unit_mg == Decimal("37.5")

    def test_gioi_han_khong_duong_bi_chan(self) -> None:
        with pytest.raises(ValueError, match="phải > 0"):
            ControlledSubstance(
                name_intl="X",
                scientific_name="x",
                appendix=ControlledSubstanceAppendix.PL_II,
                limit_per_unit_mg=Decimal("0"),
            )

    def test_ten_rong_bi_chan(self) -> None:
        with pytest.raises(ValueError, match="không được để trống"):
            ControlledSubstance(
                name_intl="  ", scientific_name="x", appendix=ControlledSubstanceAppendix.PL_I
            )

    def test_moc_hieu_luc_rieng_cua_etomidate_carisoprodol(self) -> None:
        """TT18 Điều 16.2 — 2 chất này là hướng thần từ 01/6/2026, sớm hơn hiệu lực chung."""
        etomidate = ControlledSubstance(
            name_intl="ETOMIDATE",
            scientific_name="Ethyl3-[(1R)-1-phenylethyl]imidazole-5-carboxylate",
            appendix=ControlledSubstanceAppendix.PL_II,
            effective_from=date(2026, 6, 1),
        )
        assert etomidate.is_effective_on(date(2026, 5, 31)) is False
        assert etomidate.is_effective_on(date(2026, 6, 1)) is True

    def test_chat_khong_co_moc_rieng_luon_hieu_luc(self) -> None:
        chat = ControlledSubstance(
            name_intl="CODEINE; 3-METHYLMORPHINE",
            scientific_name="(5α, 6α)-7,8-didehydro-4,5-epoxy-3- methoxy-17-methylmorphinan-6-ol",
            appendix=ControlledSubstanceAppendix.PL_I,
            limit_per_unit_mg=Decimal("100"),
            limit_concentration_pct=Decimal("2.5"),
        )
        assert chat.is_effective_on(date(2017, 1, 1)) is True

    def test_ghi_chu_gioi_han_dang_van_ban(self) -> None:
        """PL IV có 2 dòng ngưỡng là câu điều kiện, không phải số — giữ nguyên văn."""
        chat = ControlledSubstance(
            name_intl="DIPHENOXYLATE",
            scientific_name=(
                "1-(3-cyano-3,3-diphenylpropyl)-4-phenylpiperidine- 4- carboxylic acid ethyl ester"
            ),
            appendix=ControlledSubstanceAppendix.PL_I,
            limit_note=(
                "Không quá 2,5 mg Diphenoxylate và với ít nhất 0,025 mg Atropin Sulfat "
                "trong một đơn vị sản phẩm đã chia liều."
            ),
        )
        assert chat.limit_per_unit_mg is None
        assert "Atropin Sulfat" in (chat.limit_note or "")


class TestLedgerBookType:
    """2 mẫu sổ xuất/nhập/tồn của TT18 — Phụ lục VIII và Phụ lục XVI (Điều 12.1.a / 12.3)."""

    @pytest.mark.parametrize(
        "category",
        [
            ControlledSubstanceCategory.GAY_NGHIEN,
            ControlledSubstanceCategory.HUONG_THAN,
            ControlledSubstanceCategory.TIEN_CHAT,
        ],
    )
    def test_gn_ht_tc_ghi_so_phu_luc_viii(self, category: ControlledSubstanceCategory) -> None:
        assert book_type_for(category) is LedgerBookType.PL_VIII

    @pytest.mark.parametrize(
        "category",
        [
            ControlledSubstanceCategory.PHOI_HOP_GN,
            ControlledSubstanceCategory.PHOI_HOP_HT,
            ControlledSubstanceCategory.PHOI_HOP_TC,
            ControlledSubstanceCategory.THUOC_DOC,
            ControlledSubstanceCategory.DANH_MUC_CAM,
        ],
    )
    def test_phoi_hop_doc_va_cam_ghi_so_phu_luc_xvi(
        self, category: ControlledSubstanceCategory
    ) -> None:
        """Điều 12.3 — nghĩa vụ MỚI của bán lẻ, TT20/2017 không có."""
        assert book_type_for(category) is LedgerBookType.PL_XVI

    def test_thuoc_thuong_khong_co_so(self) -> None:
        with pytest.raises(NotControlledSubstanceError):
            book_type_for(ControlledSubstanceCategory.NONE)


class TestBanThuocDocVaDanhMucCam:
    """Điều 12.3 chỉ buộc sổ xuất/nhập/tồn — KHÔNG có nghĩa vụ sổ khách hàng (Phụ lục XIX)."""

    @pytest.mark.parametrize(
        "category",
        [ControlledSubstanceCategory.THUOC_DOC, ControlledSubstanceCategory.DANH_MUC_CAM],
    )
    def test_ban_ra_khong_doi_thong_tin_khach_hang(
        self, category: ControlledSubstanceCategory
    ) -> None:
        validate_controlled_sale(category, prescription_code=None, customer=None)

    @pytest.mark.parametrize(
        "category",
        [
            ControlledSubstanceCategory.PHOI_HOP_GN,
            ControlledSubstanceCategory.PHOI_HOP_HT,
            ControlledSubstanceCategory.PHOI_HOP_TC,
        ],
    )
    def test_dang_phoi_hop_van_doi_thong_tin_khach_hang(
        self, category: ControlledSubstanceCategory
    ) -> None:
        """Điều 12.2 — bán lẻ thuốc dạng phối hợp vẫn phải lập Sổ theo dõi khách hàng."""
        with pytest.raises(MissingControlledCustomerDetailError):
            validate_controlled_sale(category, prescription_code=None, customer=None)

    def test_ghi_so_duoc_cho_thuoc_doc(self) -> None:
        entry = ControlledLedgerEntry(
            tenant_id=uuid4(),
            branch_id=uuid4(),
            drug_id=uuid4(),
            category=ControlledSubstanceCategory.THUOC_DOC,
            direction=LedgerDirection.NHAP,
            quantity=Decimal("10"),
            lot_no="L1",
            expiry_date=date(2027, 1, 1),
            transaction_at=datetime(2026, 7, 20, tzinfo=UTC),
            source_or_destination="NCC A",
            document_no="PXK-1",
        )
        assert book_type_for(entry.category) is LedgerBookType.PL_XVI


class TestLedgerPeriodAggregate:
    """Tổng theo kỳ cho báo cáo định kỳ Mẫu số 06 (docs/13 mục C.7 — NĐ163 Điều 35.2)."""

    def test_closing_balance_cong_dau_ky_voi_nhap_tru_xuat(self) -> None:
        agg = LedgerPeriodAggregate(
            drug_id=uuid4(),
            category=ControlledSubstanceCategory.HUONG_THAN,
            opening_balance=Decimal("100"),
            received_in_period=Decimal("50"),
            issued_in_period=Decimal("30"),
        )
        assert agg.closing_balance == Decimal("120")

    def test_closing_balance_khong_am_khi_xuat_het(self) -> None:
        agg = LedgerPeriodAggregate(
            drug_id=uuid4(),
            category=ControlledSubstanceCategory.GAY_NGHIEN,
            opening_balance=Decimal("10"),
            received_in_period=Decimal("0"),
            issued_in_period=Decimal("10"),
        )
        assert agg.closing_balance == Decimal("0")


class TestReturnedDrugItem:
    """Một dòng trong bảng thuốc nhận lại (Phụ lục XVIII, docs/13 mục C.6)."""

    def test_quantity_duong_hop_le(self) -> None:
        item = ReturnedDrugItem(
            description="Diazepam 5mg, viên nén, hộp 2 vỉ x 10 viên, SĐK VD-12345-26",
            unit="viên",
            quantity=Decimal("3"),
            lot_no="L20260101",
            expiry_date=date(2028, 1, 1),
            condition_note="Còn nguyên vỉ, không biến đổi màu sắc",
            reason="Người bệnh không dùng hết",
        )
        assert item.quantity == Decimal("3")

    def test_quantity_khong_duong_bi_chan(self) -> None:
        with pytest.raises(ValueError, match="phải > 0"):
            ReturnedDrugItem(
                description="X",
                unit="viên",
                quantity=Decimal("0"),
                lot_no="L1",
                expiry_date=date(2028, 1, 1),
                condition_note="",
                reason="",
            )


class TestDrugReturnRecord:
    """Biên bản nhận lại thuốc GN/HT/TC (docs/13 mục C.6)."""

    def _item(self) -> ReturnedDrugItem:
        return ReturnedDrugItem(
            description="Diazepam 5mg",
            unit="viên",
            quantity=Decimal("3"),
            lot_no="L20260101",
            expiry_date=date(2028, 1, 1),
            condition_note="Còn nguyên vỉ",
            reason="Không dùng hết",
        )

    def test_bien_ban_hop_le(self) -> None:
        record = DrugReturnRecord(
            tenant_id=uuid4(),
            branch_id=uuid4(),
            returner_name="Nguyễn Văn A",
            returner_address="12 Lê Lợi, Q1, HCM",
            returner_id_number="079123456789",
            returner_id_issuer="Cục Cảnh sát QLHC về TTXH",
            returner_id_issued_at=date(2021, 5, 1),
            returner_is_patient=True,
            receiving_pharmacist_name="DS. Trần Thị B",
            items=[self._item()],
            handover_at=datetime(2026, 7, 25, 14, 30, tzinfo=UTC),
            handover_location="Nhà thuốc ABC, 12 Lê Lợi, Q1, HCM",
        )
        assert record.items[0].quantity == Decimal("3")
        assert record.returner_is_patient is True

    def test_bien_ban_khong_the_khong_co_dong_thuoc_nao(self) -> None:
        with pytest.raises(ValueError, match="ít nhất 1 dòng thuốc"):
            DrugReturnRecord(
                tenant_id=uuid4(),
                branch_id=uuid4(),
                returner_name="Nguyễn Văn A",
                returner_address="12 Lê Lợi",
                returner_id_number="079123456789",
                returner_id_issuer="Cục Cảnh sát QLHC về TTXH",
                returner_id_issued_at=date(2021, 5, 1),
                returner_is_patient=True,
                receiving_pharmacist_name="DS. Trần Thị B",
                items=[],
                handover_at=datetime(2026, 7, 25, 14, 30, tzinfo=UTC),
                handover_location="Nhà thuốc ABC",
            )


class TestLedgerBookSignature:
    """Xác nhận điện tử cho 1 sổ/1 ngày, hướng A (docs/13 mục C.5, bước 6/6 TT18)."""

    _HASH_A = "a" * 64
    _HASH_B = "b" * 64

    def test_hop_le_khong_co_prev_hash(self) -> None:
        sig = LedgerBookSignature(
            tenant_id=uuid4(),
            book_type=LedgerBookType.PL_VIII,
            book_date=date(2026, 7, 25),
            content_sha256=self._HASH_A,
            prev_hash=None,
            signed_by_user_id=uuid4(),
        )
        assert sig.prev_hash is None
        assert sig.content_sha256 == self._HASH_A

    def test_hop_le_co_prev_hash_moc_xich(self) -> None:
        sig = LedgerBookSignature(
            tenant_id=uuid4(),
            book_type=LedgerBookType.PL_XVI,
            book_date=date(2026, 7, 26),
            content_sha256=self._HASH_B,
            prev_hash=self._HASH_A,
            signed_by_user_id=uuid4(),
        )
        assert sig.prev_hash == self._HASH_A

    def test_content_sha256_sai_do_dai_bi_chan(self) -> None:
        with pytest.raises(ValueError, match="content_sha256"):
            LedgerBookSignature(
                tenant_id=uuid4(),
                book_type=LedgerBookType.PL_VIII,
                book_date=date(2026, 7, 25),
                content_sha256="not-a-real-hash",
                prev_hash=None,
                signed_by_user_id=uuid4(),
            )

    def test_prev_hash_sai_do_dai_bi_chan(self) -> None:
        with pytest.raises(ValueError, match="prev_hash"):
            LedgerBookSignature(
                tenant_id=uuid4(),
                book_type=LedgerBookType.PL_VIII,
                book_date=date(2026, 7, 25),
                content_sha256=self._HASH_A,
                prev_hash="too-short",
                signed_by_user_id=uuid4(),
            )
