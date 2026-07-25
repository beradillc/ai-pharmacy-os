"""Kết xuất Sổ xuất/nhập/tồn — TT 18/2026 Phụ lục VIII và XVI (docs/13 mục C.2.1)."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from pharmacy_os.modules.compliance.application import (
    LEDGER_BOOK_CSV_HEADER,
    ledger_book_row_to_csv,
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
