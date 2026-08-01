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

import csv
import io
from collections.abc import Iterable, Iterator, Mapping
from decimal import Decimal
from uuid import UUID

from pharmacy_os.modules.compliance.application.dto import LedgerBookRow, PeriodicReportRow
from pharmacy_os.modules.compliance.domain import ControlledLedgerEntry, LedgerDirection
from pharmacy_os.modules.compliance.domain.ports import DrugMasterFacts, LedgerPeriodAggregate

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


def to_book_rows(
    entries: Iterable[ControlledLedgerEntry],
    opening: Mapping[UUID, Decimal] | None = None,
) -> Iterator[LedgerBookRow]:
    """Tính cột (6) "Còn lại" — tồn lũy kế, **cộng dồn riêng cho từng thuốc**.

    Mẫu sổ bắt mỗi thuốc một sổ riêng nên tồn lũy kế reset khi sang thuốc khác. Đầu vào
    phải đã sắp theo (thuốc, thời điểm) — đúng thứ tự ``list_for_book`` trả về.

    ``opening`` là **tồn đầu kỳ** từng thuốc (Σ mọi bút toán trước ngày bắt đầu kỳ). Thiếu
    nó thì mỗi thuốc bắt đầu từ 0.

    🔴 **Bỏ ``opening`` là một lỗi, không phải một lựa chọn** — phát hiện 2026-08-01 khi
    dựng màn C-03. Bản đầu của hàm này luôn khởi động từ 0, nên kết xuất sổ cho bất kỳ kỳ
    nào **không bắt đầu từ bút toán đầu tiên** đều cho cột "Còn lại" sai. Màn hình lộ ra
    ngay ở lượt chạy đầu: một kỳ chỉ chứa một dòng XUẤT 5 hiện **`Còn lại: −5`**. Trên tệp
    CSV đem trình thanh tra, một sổ thuốc gây nghiện tồn âm đọc như *"đã bán thuốc chưa
    từng nhập"*.

    Tham số **tuỳ chọn** chứ không bắt buộc (kỷ luật #17): bên gọi cũ và các test đã có giữ
    nguyên hành vi. Đường thật — ``ComplianceService.ledger_book_rows`` — luôn truyền.
    """
    opening = opening or {}
    balance = Decimal(0)
    current_drug = None
    for entry in entries:
        if entry.drug_id != current_drug:
            current_drug = entry.drug_id
            balance = opening.get(entry.drug_id, Decimal(0))
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


def render_ledger_book_csv_text(rows: Iterable[LedgerBookRow]) -> str:
    """Toàn bộ nội dung CSV của sổ (header + mọi dòng) thành 1 chuỗi, không streaming.

    Dùng cho báo cáo kết xuất cuối ngày (docs/13 mục C.5, ghi chú Phụ lục VIII: "trích xuất,
    in cuối mỗi ngày") — cần **chính chuỗi này** để băm SHA-256 rồi phát cùng nội dung tải về,
    nên phải dựng xong toàn bộ trước khi trả response, khác cách streaming từng dòng của
    :func:`ledger_book_row_to_csv` dùng cho export theo kỳ dài (không thể băm trước khi biết
    hết nội dung). An toàn về bộ nhớ vì phạm vi luôn là **1 ngày**, không phải cả kỳ.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(LEDGER_BOOK_CSV_HEADER)
    for row in rows:
        writer.writerow(ledger_book_row_to_csv(row))
    return buffer.getvalue()


#: Thứ tự cột của báo cáo định kỳ, bám Mẫu số 06 Phụ lục II NĐ163 cột (1)–(12). ``ten_co_so``,
#: kỳ báo cáo, chữ ký... nằm ở phần đầu/cuối mẫu, không phải cột bảng — không xuất ở đây, người
#: dùng điền khi ghép vào biểu mẫu chính thức.
PERIODIC_REPORT_CSV_HEADER: tuple[str, ...] = (
    "tt",  # (1)
    "ten_thuoc_day_du",  # (2) tên/dạng bào chế/hoạt chất/nồng độ-hàm lượng/quy cách/số ĐKLH
    "nuoc_san_xuat",  # (3)
    "don_vi_tinh",  # (4)
    "so_cong_van_cho_phep_mua",  # (5)
    "ton_ky_truoc",  # (6)
    "nhap_trong_ky",  # (7)
    "tong_so",  # (8)
    "xuat_trong_ky",  # (9)
    "ton_cuoi_ky",  # (10)
    "hao_hut",  # (11)
    "ghi_chu",  # (12)
    "drug_id",  # ngoài mẫu — đối chiếu nội bộ
)


def _mo_ta_thuoc(row: PeriodicReportRow) -> str:
    """Cột (2) Mẫu số 06 — ghép các phần đã biết, bỏ qua phần không có dữ liệu.

    ``packaging_spec``/``registration_no`` có thể ``None`` (chưa lưu ở catalog hoặc thuốc chưa
    có số ĐKLH) — bỏ qua phần đó thay vì in "None" hay để dấu phẩy trống giữa các phần.
    """
    parts = [row.drug_name]
    if row.dosage_form:
        parts.append(row.dosage_form)
    if row.active_ingredients:
        parts.append(row.active_ingredients)
    if row.strength:
        parts.append(row.strength)
    if row.packaging_spec:
        parts.append(row.packaging_spec)
    if row.registration_no:
        parts.append(f"SĐK {row.registration_no}")
    return ", ".join(parts)


def periodic_report_row_to_csv(index: int, row: PeriodicReportRow) -> list[str]:
    """Một dòng báo cáo định kỳ thành list ô chuỗi, khớp :data:`PERIODIC_REPORT_CSV_HEADER`.

    ``index`` là số thứ tự (1-based) trong file — không phải thuộc tính của ``row``, vì thứ tự
    chỉ có ý nghĩa tại thời điểm xuất (phụ thuộc cách sắp xếp của người gọi), không phải dữ liệu
    cố hữu của một dòng báo cáo.
    """
    return [
        str(index),
        _mo_ta_thuoc(row),
        row.manufacturing_country or "",
        row.unit,
        row.purchase_permit_no or "",
        _so_luong(row.opening_balance),
        _so_luong(row.received_in_period),
        _so_luong(row.total),
        _so_luong(row.issued_in_period),
        _so_luong(row.closing_balance),
        _so_luong(row.shrinkage) if row.shrinkage else "",
        row.note or "",
        str(row.drug_id),
    ]


def to_periodic_report_rows(
    aggregates: Iterable[LedgerPeriodAggregate],
    drug_facts: Mapping[UUID, DrugMasterFacts],
) -> list[PeriodicReportRow]:
    """Ghép số liệu ledger (đã tổng theo kỳ) với thông tin thuốc từ catalog.

    Thuốc không tra được trong ``drug_facts`` (đã xóa khỏi catalog nhưng còn lịch sử giao dịch)
    vẫn phải xuất hiện — không được âm thầm bỏ sót một dòng khỏi báo cáo pháp lý chỉ vì thiếu
    tên hiển thị. Dùng ``drug_id`` làm tên tạm trong trường hợp đó.
    """
    rows = []
    for agg in aggregates:
        facts = drug_facts.get(agg.drug_id)
        rows.append(
            PeriodicReportRow(
                drug_id=agg.drug_id,
                drug_name=facts.name if facts is not None else f"[không rõ: {agg.drug_id}]",
                dosage_form=facts.form if facts is not None else None,
                active_ingredients=facts.active_ingredients if facts is not None else "",
                strength=facts.strength if facts is not None else None,
                registration_no=facts.registration_no if facts is not None else None,
                unit=facts.base_unit if facts is not None else "",
                opening_balance=agg.opening_balance,
                received_in_period=agg.received_in_period,
                total=agg.opening_balance + agg.received_in_period,
                issued_in_period=agg.issued_in_period,
                closing_balance=agg.closing_balance,
            )
        )
    return rows
