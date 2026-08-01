"""Kết xuất hoá đơn — người bán và khổ giấy K80 (Chain giao 2026-08-01).

🔴 Trước lượt này `receipt_rendering.py` **không có test nào**. Nó vẫn "xanh" suốt vì
không ai hỏi nó câu gì — đúng loại cổng-bằng-không kiểm toán 26/07 đếm được. Ba khẳng
định dưới đây là ba câu hỏi cụ thể, và cả ba đã được xem đỏ trước khi tin (kỷ luật #14).
"""

import re
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from pharmacy_os.core.config import OrgSettings
from pharmacy_os.modules.sales.application.dto import (
    ReceiptLine,
    ReceiptPayment,
    ReceiptSummaryDTO,
)
from pharmacy_os.modules.sales.domain import PaymentMethod
from pharmacy_os.modules.sales.interface.receipt_rendering import (
    render_pdf,
    render_thermal_k80,
)

_ORG = OrgSettings(pharmacy_name="Nhà thuốc 650")

#: 80mm quy ra point: 80 / 25.4 * 72 = 226,77.
_K80_POINTS = 226.77


def _hoa_don(*, nguoi_ban: str | None = "Trịnh Thư", so_dong: int = 1) -> ReceiptSummaryDTO:
    return ReceiptSummaryDTO(
        order_id=uuid4(),
        tenant_id=uuid4(),
        branch_id=uuid4(),
        created_at=datetime(2026, 8, 1, 9, 30, tzinfo=UTC),
        client_uuid="hd-1",
        currency="VND",
        status="COMPLETED",
        lines=[
            ReceiptLine(
                drug_id=uuid4(),
                name=f"Paracetamol 500mg {i}",
                unit="viên",
                quantity=Decimal("2"),
                unit_price=Decimal("10000"),
                line_total=Decimal("20000"),
            )
            for i in range(so_dong)
        ],
        payments=[ReceiptPayment(method=PaymentMethod.CASH, amount=Decimal("25000"))],
        subtotal=Decimal("20000"),
        paid_total=Decimal("25000"),
        change_amount=Decimal("5000"),
        prescription_ref=None,
        sold_by_name=nguoi_ban,
    )


def _be_ngang_pdf(pdf: bytes) -> float:
    """Bề ngang trang, đọc từ `/MediaBox` của chính tệp PDF.

    Đo trên SẢN PHẨM chứ không tin hằng số trong mã: cổng phải biết đổi màu khi ai đó sửa
    khổ giấy, và một khẳng định `_K80_PAGE_WIDTH == 80 * mm` chỉ chứng minh phép nhân.
    """
    m = re.search(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", pdf)
    assert m is not None, "PDF không có /MediaBox — không đọc được khổ giấy"
    return float(m.group(3)) - float(m.group(1))


def test_bill_nhiet_co_dong_nguoi_ban() -> None:
    assert "Người bán: Trịnh Thư" in render_thermal_k80(_hoa_don(), _ORG)


def test_khong_tra_duoc_ten_thi_BO_HAN_dong_nguoi_ban() -> None:
    """Không in `Người bán:` rỗng — một dòng cụt trên tờ giấy đưa khách trông như lỗi."""
    assert "Người bán" not in render_thermal_k80(_hoa_don(nguoi_ban=None), _ORG)


def test_pdf_k80_rong_dung_80mm() -> None:
    assert abs(_be_ngang_pdf(render_pdf(_hoa_don(), _ORG, "K80")) - _K80_POINTS) < 1.0


def test_pdf_a5_van_giu_nguyen_kho_cu() -> None:
    """Khổ K80 là đường THÊM VÀO, không được đụng hai khổ đang dùng (kỷ luật #17)."""
    assert _be_ngang_pdf(render_pdf(_hoa_don(), _ORG, "A5")) > _K80_POINTS * 1.5


def test_pdf_k80_dai_ra_theo_so_dong() -> None:
    """Giấy cuộn không có "trang": hoá đơn 12 món phải dài hơn hoá đơn 1 món.

    Khổ cố định sẽ hoặc cắt cụt hoá đơn dài, hoặc nhả thừa cả gang giấy cho hoá đơn hai
    món — và cái cắt cụt thì **không ai thấy** cho tới lúc khách hỏi dòng tiền thối.
    """
    ngan = render_pdf(_hoa_don(so_dong=1), _ORG, "K80")
    dai = render_pdf(_hoa_don(so_dong=12), _ORG, "K80")

    def cao(pdf: bytes) -> float:
        m = re.search(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", pdf)
        assert m is not None
        return float(m.group(4)) - float(m.group(2))

    assert cao(dai) > cao(ngan)


def test_pdf_k80_co_du_tien_thoi_va_nguoi_ban() -> None:
    """Nội dung PDF K80 không được rụng mất so với bản nhiệt.

    Không đọc chữ từ PDF (font nhúng làm việc đó không đáng tin) — đo GIÁN TIẾP: bản K80
    có người bán phải dài hơn bản không có, vì `_k80_page_height` cộng thêm một dòng.
    """
    co_ten = render_pdf(_hoa_don(), _ORG, "K80")
    khong_ten = render_pdf(_hoa_don(nguoi_ban=None), _ORG, "K80")

    def cao(pdf: bytes) -> float:
        m = re.search(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", pdf)
        assert m is not None
        return float(m.group(4)) - float(m.group(2))

    assert cao(co_ten) > cao(khong_ten)
