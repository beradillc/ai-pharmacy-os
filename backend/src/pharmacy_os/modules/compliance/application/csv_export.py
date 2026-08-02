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
from datetime import date
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


#: Tiêu đề cột của Mẫu số 06 — **chữ của bản gốc**, không phải tên biến.
#:
#: 🔴 Đổi 2026-08-02 cùng lượt đóng N-2. Trước đó cột ghi tên máy (``ten_thuoc_day_du``,
#: ``so_cong_van_cho_phep_mua``) — chấp nhận được khi tệp chỉ là *dữ liệu để người dùng chép
#: sang biểu mẫu*. Nhưng từ khi tệp mang **tiêu đề chính thức, dòng "Kính gửi", ô ký và con
#: dấu**, nó không còn là dữ liệu nữa mà **chính là văn bản đem nộp** — và một văn bản nộp cơ
#: quan quản lý có dòng tiêu đề ``ten_thuoc_day_du`` thì người ta sẽ nộp đúng như thế.
#:
#: An toàn để đổi: đã rà, **không bên gọi máy nào** đọc tệp này (`grep` toàn frontend chỉ ra
#: một nhãn hiển thị trong màn Nhật ký, không phải bên phân tích cú pháp). Nếu về sau có bên
#: tích hợp, cần một endpoint riêng dạng máy-đọc — không phải nới tệp này ra làm hai việc.
#:
#: Số ``(1)``–``(12)`` giữ nguyên trong ngoặc vì bản gốc đánh số cột, và người đối chiếu với
#: biểu mẫu giấy tra theo số chứ không theo chữ.
PERIODIC_REPORT_CSV_HEADER: tuple[str, ...] = (
    "TT (1)",
    "Tên thuốc, dạng bào chế, hoạt chất, nồng độ/hàm lượng, quy cách đóng gói, "
    "số giấy đăng ký lưu hành (2)",
    "Nước sản xuất (3)",
    "Đơn vị tính (4)",
    "Số công văn cho phép mua trong nước (5)",
    "Số lượng tồn kho kỳ trước chuyển sang (6)",
    "Số lượng nhập trong kỳ (7)",
    "Tổng số (8)",
    "Số lượng xuất trong kỳ (9)",
    "Tồn kho cuối kỳ (10)",
    "Số lượng hao hụt (11)",
    "Ghi chú (12)",
    # Ngoài biểu mẫu — để đối chiếu nội bộ khi có tranh chấp số liệu. Nói rõ trên chính tiêu
    # đề cột để người nộp biết đây là cột phải xoá, thay vì đoán.
    "[nội bộ, không thuộc biểu mẫu] drug_id",
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


#: Tiêu đề chính thức của Mẫu số 06, **chép nguyên văn** từ bản gốc
#: `docs/legal/Nghị-định-163-2025-NĐ-CP.docx` (Phụ lục II, Mẫu số 06). Dài và liệt kê đủ mọi
#: loại thuốc vì bản gốc đúng là như vậy — một cơ sở bán lẻ nộp báo cáo phải gạch bỏ phần
#: không áp dụng, đó là cách biểu mẫu này vận hành.
#:
#: 🔴 KHÔNG rút gọn, KHÔNG diễn đạt lại. Đây là chuỗi đi vào một văn bản nộp cơ quan quản lý; sửa
#: chữ cho "gọn hơn" là sửa biểu mẫu pháp lý. Quy tắc R-10 của vault: kết luận về nghĩa vụ pháp lý
#: phải đọc bản gốc, không suy từ trí nhớ — chuỗi này lấy bằng cách giải nén chính tệp .docx.
MAU_06_TIEU_DE = (
    "BÁO CÁO ĐỊNH KỲ XUẤT, NHẬP, TỒN KHO, SỬ DỤNG THUỐC GÂY NGHIỆN/THUỐC HƯỚNG THẦN/"
    "THUỐC TIỀN CHẤT/THUỐC DẠNG PHỐI HỢP CHỨA DƯỢC CHẤT GÂY NGHIỆN/THUỐC DẠNG PHỐI HỢP "
    "CHỨA DƯỢC CHẤT HƯỚNG THẦN/THUỐC DẠNG PHỐI HỢP CHỨA TIỀN CHẤT/THUỐC PHÓNG XẠ, "
    "NGUYÊN LIỆU LÀM THUỐC LÀ CHẤT PHÓNG XẠ, THUỐC ĐỘC, NGUYÊN LIỆU ĐỘC LÀM THUỐC, "
    "THUỐC, DƯỢC CHẤT TRONG DANH MỤC THUỐC, DƯỢC CHẤT THUỘC DANH MỤC CHẤT BỊ CẤM SỬ DỤNG "
    "TRONG MỘT SỐ NGÀNH, LĨNH VỰC CỦA CƠ SỞ BÁN BUÔN, BÁN LẺ, CƠ SỞ TỔ CHỨC CHUỖI NHÀ THUỐC"
)


def _ngay_vn(d: date) -> str:
    """`dd/mm/yyyy` — định dạng của văn bản hành chính Việt Nam, không phải ISO."""
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def mau_06_phan_dau(
    *,
    ten_co_so: str,
    dia_chi: str,
    tu_ngay: date,
    den_ngay: date,
) -> list[list[str]]:
    """Phần đầu Mẫu số 06 — đóng nợ **N-2**.

    Trước đây tệp CSV xuất ra **chỉ có bảng 12 cột**, không có gì cho biết nó là báo cáo của
    cơ sở nào, kỳ nào, gửi ai. Người dùng phải tự nhớ ghép vào biểu mẫu chính thức — và một
    tệp báo cáo pháp lý **không tự nói được nó là báo cáo gì** là thứ rất dễ nộp nhầm kỳ.

    Bố cục bám đúng bản gốc (Phụ lục II NĐ163):

        TÊN CƠ SỞ__________
        Số: ……….
        <tiêu đề>
        (Kỳ báo cáo từ ngày ……….. đến ngày…………)
        Kính gửi:……………….

    🔴 **Hai ô cố ý ĐỂ TRỐNG, không đoán:**
    - ``Số:`` — số hiệu văn bản đi do cơ sở tự đánh theo sổ văn thư của mình. Hệ thống không
      giữ sổ văn thư, và sinh đại một con số là **tạo ra một số hiệu văn bản không có thật**.
    - ``Kính gửi:`` — NĐ163 Điều 35.2 ghi *"gửi Ủy ban nhân dân cấp tỉnh nơi cơ sở đặt trụ sở
      chính"*. Tỉnh suy từ chuỗi địa chỉ tự do là **đoán**: `"xã Thạnh Trị, Vĩnh Long"` tách
      được, `"650 Nguyễn Trãi, P.11, Q.5"` thì không, và đoán sai nghĩa là gửi báo cáo cho sai
      cơ quan. In sẵn địa chỉ cơ sở ngay bên cạnh để người điền có đủ dữ kiện, rồi để họ điền.
    """
    return [
        ["TÊN CƠ SỞ", ten_co_so or "……………………"],
        ["Địa chỉ", dia_chi or "……………………"],
        # Để trống có chủ đích — xem docstring. Dấu chấm lửng là ký hiệu của chính biểu mẫu gốc.
        ["Số", "………."],
        [MAU_06_TIEU_DE],
        [f"(Kỳ báo cáo từ ngày {_ngay_vn(tu_ngay)} đến ngày {_ngay_vn(den_ngay)})"],
        ["Kính gửi", "Ủy ban nhân dân cấp tỉnh nơi cơ sở đặt trụ sở chính: ……………………"],
        [],
    ]


def mau_06_phan_cuoi() -> list[list[str]]:
    """Phần cuối Mẫu số 06 — *Nơi nhận*, chỗ ký, và 2 ghi chú của bản gốc.

    Ghi chú *"Số lượng hao hụt bao gồm cả hỏng, vỡ, hết hạn dùng…"* đặc biệt đáng in ra: cột
    (11) trong tệp này **luôn để trống** (ledger không phân biệt lý do xuất), nên người điền
    cần biết chính xác cột đó đòi gì. Không in ghi chú thì cột trống trông như số 0.

    Dòng ngày tháng để trống — ngày ký là ngày người đại diện thật sự ký, không phải ngày bấm
    nút xuất tệp. Điền sẵn ngày hôm nay là **ghi một ngày ký không có thật** vào văn bản.
    """
    return [
        [],
        ["Nơi nhận:", "……, ngày …… tháng …… năm ……"],
        ["- Như trên;", "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/NGƯỜI ĐƯỢC ỦY QUYỀN"],
        ["- Lưu tại cơ sở.", "(Ký, ghi rõ họ tên, chức danh đóng dấu (nếu có))"],
        [],
        ["Ghi chú:"],
        [
            "- Cơ sở tổ chức chuỗi nhà thuốc lập báo cáo, gửi các cơ quan theo quy định tại "
            "khoản 2 Điều 35 Nghị định này; đồng thời, lập báo cáo xuất, nhập, tồn kho, sử dụng "
            "của từng nhà thuốc thuộc chuỗi nhà thuốc gửi Ủy ban nhân dân cấp tỉnh nơi có nhà "
            "thuốc hoạt động."
        ],
        ["- Số lượng hao hụt bao gồm cả hỏng, vỡ, hết hạn dùng... Nếu có, cần báo cáo chi tiết."],
        [
            "- Đối với báo cáo định kỳ 06 tháng, ngày báo cáo bắt đầu từ ngày 01 tháng 01 đến "
            "ngày 30 tháng 6 của năm báo cáo. Đối với báo cáo năm, ngày báo cáo bắt đầu từ ngày "
            "01 tháng 01 đến ngày 31 tháng 12 của năm báo cáo."
        ],
    ]
