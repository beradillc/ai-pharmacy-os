"""Shaping một dòng Sổ xuất/nhập/tồn thành ô CSV — thuần, không framework.

Cùng quy ước với ``core/audit/csv_export.py`` và ``sales/application/csv_export.py``
(PROJECT_STATE §7al): một hằng ``*_HEADER`` + một hàm thuần ``*_to_row``, tách khỏi
service để hợp đồng cột có đúng một chỗ và test được mà không cần CSDL hay HTTP.

**Cột lấy nguyên văn từ mẫu sổ pháp lý** — TT 18/2026 Phụ lục VIII (GN/HT/TC) và Phụ lục
XVI (dạng phối hợp, thuốc độc, danh mục cấm). Hai mẫu sổ có **cùng 8 cột (1)–(8)**; khác
nhau ở nhóm thuốc được ghi và ở phần đầu sổ (PL XVI có thêm dòng "Nhà sản xuất").

⚠️ **Nợ đã biết — phần ĐẦU SỔ chưa kết xuất được:** mẫu sổ còn yêu cầu ghi ở đầu mỗi sổ
``Tên cơ sở``/``Địa chỉ``/``Điện thoại``, ``Tên thuốc, nồng độ/hàm lượng``,
``Số giấy đăng ký lưu hành``, ``Đơn vị tính`` (PL XVI thêm ``Nhà sản xuất``). Những trường
này thuộc ``catalog``; đọc chúng phải mở rộng read-port ``DrugMasterFacts`` — là thay đổi
**cross-module**, phải đề xuất thiết kế và chờ duyệt (CLAUDE.md kỷ luật 2). Vì vậy bản này
kết xuất phần BẢNG của sổ kèm ``drug_id`` để đối chiếu, chưa phải sổ hoàn chỉnh in ra ký.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from decimal import Decimal

from pharmacy_os.modules.compliance.application.dto import LedgerBookRow
from pharmacy_os.modules.compliance.domain import ControlledLedgerEntry, LedgerDirection

#: Thứ tự cột của file kết xuất, bám mẫu sổ Phụ lục VIII/XVI cột (1)–(8).
#: Ổn định: thêm cột mới thì nối vào cuối, không đảo thứ tự.
LEDGER_BOOK_CSV_HEADER: tuple[str, ...] = (
    "ngay_thang",  # (1)
    "noi_xuat_nhap",  # (2)
    "so_chung_tu",  # (3)
    "so_luong_nhap",  # (4)
    "so_luong_xuat",  # (5)
    "so_luong_con_lai",  # (6)
    "so_lo_han_dung",  # (7)
    "ghi_chu",  # (8)
    "drug_id",  # ngoài mẫu — để đối chiếu khi 1 file gộp nhiều thuốc
)


def _so_luong(value: Decimal | None) -> str:
    """Bỏ số 0 thừa sau dấu thập phân — cột ``Numeric(18, 3)`` trả về "100.000".

    Sổ này in ra để ký nên phải đọc như người ghi tay: 100 chứ không phải 100.000;
    số lẻ thật (37.5) vẫn giữ nguyên.
    """
    if value is None:
        return ""
    return f"{value.normalize():f}"


def ledger_book_row_to_csv(row: LedgerBookRow) -> list[str]:
    """Một dòng sổ thành list ô chuỗi, khớp :data:`LEDGER_BOOK_CSV_HEADER`."""
    return [
        row.transaction_at.date().isoformat(),
        row.source_or_destination,
        row.document_no,
        _so_luong(row.quantity_in),
        _so_luong(row.quantity_out),
        _so_luong(row.balance),
        f"{row.lot_no} / {row.expiry_date.isoformat()}",
        row.note or "",
        str(row.drug_id),
    ]


def to_book_rows(entries: Iterable[ControlledLedgerEntry]) -> Iterator[LedgerBookRow]:
    """Tính cột (6) "Còn lại" — tồn lũy kế, **cộng dồn riêng cho từng thuốc**.

    Mẫu sổ bắt mỗi thuốc một sổ riêng nên tồn lũy kế reset khi sang thuốc khác. Đầu vào
    phải đã sắp theo (thuốc, thời điểm) — đúng thứ tự ``list_for_book`` trả về.
    """
    balance = Decimal(0)
    current_drug = None
    for entry in entries:
        if entry.drug_id != current_drug:
            current_drug = entry.drug_id
            balance = Decimal(0)
        is_in = entry.direction is LedgerDirection.NHAP
        balance += entry.quantity if is_in else -entry.quantity
        yield LedgerBookRow(
            drug_id=entry.drug_id,
            transaction_at=entry.transaction_at,
            source_or_destination=entry.source_or_destination,
            document_no=entry.document_no,
            quantity_in=entry.quantity if is_in else None,
            quantity_out=None if is_in else entry.quantity,
            balance=balance,
            lot_no=entry.lot_no,
            expiry_date=entry.expiry_date,
            note=entry.note,
        )
