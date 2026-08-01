"""Kết xuất Sổ xuất/nhập/tồn — TT 18/2026 Phụ lục VIII và XVI (docs/13 mục C.2.1)."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from pharmacy_os.modules.compliance.application import (
    LEDGER_BOOK_CSV_HEADER,
    ledger_book_row_to_csv,
    render_ledger_book_csv_text,
    to_book_rows,
)
from pharmacy_os.modules.compliance.domain import (
    ControlledLedgerEntry,
    ControlledSubstanceCategory,
    LedgerDirection,
)


def _entry(
    drug_id: object,
    direction: LedgerDirection,
    quantity: str,
    day: int,
    **overrides: object,
) -> ControlledLedgerEntry:
    base: dict[str, object] = {
        "tenant_id": uuid4(),
        "branch_id": uuid4(),
        "drug_id": drug_id,
        "category": ControlledSubstanceCategory.HUONG_THAN,
        "direction": direction,
        "quantity": Decimal(quantity),
        "lot_no": "L01",
        "expiry_date": date(2028, 1, 1),
        "transaction_at": datetime(2026, 7, day, 8, 0, tzinfo=UTC),
        "source_or_destination": "NCC A",
        "document_no": "PXK-1",
    }
    base.update(overrides)
    return ControlledLedgerEntry(**base)  # type: ignore[arg-type]


def test_header_bam_dung_8_cot_cua_mau_so() -> None:
    """Cột (1)–(8) theo mẫu sổ, cộng `drug_id` ngoài mẫu để đối chiếu."""
    assert LEDGER_BOOK_CSV_HEADER == (
        "ngay_thang",
        "noi_xuat_nhap",
        "so_chung_tu",
        "so_luong_nhap",
        "so_luong_xuat",
        "so_luong_con_lai",
        "so_lo_han_dung",
        "ghi_chu",
        "drug_id",
    )


def test_ton_luy_ke_cong_nhap_tru_xuat() -> None:
    drug = uuid4()
    rows = list(
        to_book_rows(
            [
                _entry(drug, LedgerDirection.NHAP, "100", 1),
                _entry(drug, LedgerDirection.XUAT, "30", 2),
                _entry(drug, LedgerDirection.NHAP, "10", 3),
            ]
        )
    )
    assert [r.balance for r in rows] == [Decimal("100"), Decimal("70"), Decimal("80")]


def test_moi_thuoc_mot_so_nen_ton_reset_khi_sang_thuoc_khac() -> None:
    """Ghi chú Phụ lục VIII: mỗi thuốc một sổ riêng ⇒ tồn lũy kế không được cộng dồn qua."""
    a, b = uuid4(), uuid4()
    rows = list(
        to_book_rows(
            [
                _entry(a, LedgerDirection.NHAP, "100", 1),
                _entry(a, LedgerDirection.XUAT, "40", 2),
                _entry(b, LedgerDirection.NHAP, "7", 1),
            ]
        )
    )
    assert [r.balance for r in rows] == [Decimal("100"), Decimal("60"), Decimal("7")]


def test_nhap_va_xuat_nam_o_2_cot_rieng() -> None:
    drug = uuid4()
    nhap, xuat = to_book_rows(
        [_entry(drug, LedgerDirection.NHAP, "5", 1), _entry(drug, LedgerDirection.XUAT, "2", 2)]
    )
    assert (nhap.quantity_in, nhap.quantity_out) == (Decimal("5"), None)
    assert (xuat.quantity_in, xuat.quantity_out) == (None, Decimal("2"))


def test_dong_csv_khop_thu_tu_header() -> None:
    drug = uuid4()
    (row,) = to_book_rows([_entry(drug, LedgerDirection.NHAP, "5", 4, note="ghi chú")])
    cells = ledger_book_row_to_csv(row)
    assert len(cells) == len(LEDGER_BOOK_CSV_HEADER)
    assert cells[0] == "2026-07-04"
    assert cells[3] == "5"
    assert cells[4] == ""  # cột Xuất bỏ trống ở dòng nhập
    assert cells[5] == "5"
    assert cells[6] == "L01 / 2028-01-01"
    assert cells[7] == "ghi chú"
    assert cells[8] == str(drug)


def test_so_rong_khong_sinh_dong_nao() -> None:
    assert list(to_book_rows([])) == []


def test_so_luong_bo_so_0_thua_nhung_giu_so_le_that() -> None:
    """Cột Numeric(18,3) trả 100.000 — sổ in ra để ký phải đọc như người ghi tay."""
    drug = uuid4()
    nhap, xuat = to_book_rows(
        [
            _entry(drug, LedgerDirection.NHAP, "100.000", 1),
            _entry(drug, LedgerDirection.XUAT, "37.500", 2),
        ]
    )
    assert ledger_book_row_to_csv(nhap)[3] == "100"
    assert ledger_book_row_to_csv(xuat)[4] == "37.5"
    assert ledger_book_row_to_csv(xuat)[5] == "62.5"


class TestRenderLedgerBookCsvText:
    """docs/13 mục C.5 — kết xuất cuối ngày, chuỗi CSV đầy đủ để băm SHA-256."""

    def test_co_header_va_moi_dong(self) -> None:
        drug = uuid4()
        rows = list(to_book_rows([_entry(drug, LedgerDirection.NHAP, "5", 4)]))
        text = render_ledger_book_csv_text(rows)
        lines = [line for line in text.splitlines() if line]
        assert lines[0].split(",")[0] == "ngay_thang"
        assert len(lines) == 2  # header + 1 dòng

    def test_rong_chi_co_header(self) -> None:
        text = render_ledger_book_csv_text([])
        lines = [line for line in text.splitlines() if line]
        assert len(lines) == 1

    def test_cung_noi_dung_cho_ra_cung_hash(self) -> None:
        """Điều kiện tiên quyết để hash có ý nghĩa làm bằng chứng toàn vẹn: xác định, không
        phụ thuộc thời điểm gọi hay thứ tự object trong bộ nhớ."""
        drug = uuid4()
        rows_a = list(to_book_rows([_entry(drug, LedgerDirection.NHAP, "5", 4)]))
        rows_b = list(to_book_rows([_entry(drug, LedgerDirection.NHAP, "5", 4)]))
        assert render_ledger_book_csv_text(rows_a) == render_ledger_book_csv_text(rows_b)

    def test_doi_1_ky_tu_lam_doi_noi_dung(self) -> None:
        drug = uuid4()
        rows = list(to_book_rows([_entry(drug, LedgerDirection.NHAP, "5", 4, note="A")]))
        rows_khac = list(to_book_rows([_entry(drug, LedgerDirection.NHAP, "5", 4, note="B")]))
        assert render_ledger_book_csv_text(rows) != render_ledger_book_csv_text(rows_khac)


class TestTonDauKy:
    """Cột "Còn lại" phải cộng tiếp từ **tồn đầu kỳ**, không khởi động lại từ 0.

    🔴 Lỗi thật, phát hiện 2026-08-01 khi dựng màn C-03 (UAT). Bản cũ của
    :func:`to_book_rows` luôn bắt đầu từ 0 cho mỗi thuốc, nên **mọi** lần kết xuất sổ cho
    một kỳ không bắt đầu từ bút toán đầu tiên đều cho cột tồn lũy kế sai — và ÂM ngay khi
    kỳ mở đầu bằng một dòng xuất.

    Vì sao nặng: tệp CSV này là thứ **đem trình thanh tra**. Một sổ thuốc gây nghiện hiện
    tồn âm đọc như *"đã bán thuốc chưa từng nhập"*. Lỗi im lặng từ Sprint 7 vì không cổng
    nào so con số ấy với thực tế — cổng đầu tiên tôi viết cho màn C-03 cũng suýt bỏ qua,
    vì nó so API với API và **cả hai cùng sai một kiểu**.
    """

    def test_khong_co_ton_dau_ky_thi_am(self) -> None:
        """Chính là hành vi cũ — giữ lại làm chứng cho vì sao tham số này phải tồn tại."""
        drug = uuid4()
        (row,) = to_book_rows([_entry(drug, LedgerDirection.XUAT, "5", 4)])
        assert row.balance == Decimal("-5")

    def test_ton_dau_ky_duoc_cong_tiep(self) -> None:
        drug = uuid4()
        (row,) = to_book_rows([_entry(drug, LedgerDirection.XUAT, "5", 4)], {drug: Decimal("100")})
        assert row.balance == Decimal("95")

    def test_moi_thuoc_dung_ton_dau_ky_cua_rieng_no(self) -> None:
        """Mẫu sổ bắt mỗi thuốc một sổ riêng — tồn đầu kỳ cũng phải riêng, không cộng lẫn."""
        a, b = uuid4(), uuid4()
        rows = list(
            to_book_rows(
                [
                    _entry(a, LedgerDirection.XUAT, "5", 4),
                    _entry(b, LedgerDirection.NHAP, "3", 4),
                ],
                {a: Decimal("100"), b: Decimal("20")},
            )
        )
        assert [r.balance for r in rows] == [Decimal("95"), Decimal("23")]

    def test_thuoc_khong_co_trong_ton_dau_ky_bat_dau_tu_0(self) -> None:
        """Thuốc chưa từng có bút toán nào trước kỳ — bắt đầu từ 0, không nổ."""
        a, b = uuid4(), uuid4()
        rows = list(
            to_book_rows(
                [
                    _entry(a, LedgerDirection.NHAP, "5", 4),
                    _entry(b, LedgerDirection.NHAP, "3", 4),
                ],
                {a: Decimal("100")},
            )
        )
        assert [r.balance for r in rows] == [Decimal("105"), Decimal("3")]

    def test_ton_dau_ky_rong_giu_nguyen_hanh_vi_cu(self) -> None:
        """Tham số tuỳ chọn (kỷ luật #17): bên gọi cũ không truyền gì thì không đổi gì."""
        drug = uuid4()
        (a,) = to_book_rows([_entry(drug, LedgerDirection.NHAP, "5", 4)])
        (b,) = to_book_rows([_entry(drug, LedgerDirection.NHAP, "5", 4)], {})
        assert a.balance == b.balance == Decimal("5")
