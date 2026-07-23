"""Render a :class:`ReceiptSummaryDTO` as thermal K80 text or A5/A4 PDF (In bill, S7).

Rút gọn theo quyết định của sếp (2026-07-23): không tính VAT, chữ ký chỉ là
khoảng trống trên giấy in — không có chữ ký điện tử/xác thực nào ở đây.
"""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Literal

from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from pharmacy_os.core.config import OrgSettings
from pharmacy_os.modules.sales.application.dto import ReceiptSummaryDTO

K80_WIDTH = 48

_PAYMENT_LABELS = {
    "CASH": "Tiền mặt",
    "CARD": "Thẻ",
    "TRANSFER": "Chuyển khoản",
    "EWALLET": "Ví điện tử",
}

_UNICODE_FONT_NAME = "ReceiptUnicode"
_UNICODE_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
)
_resolved_font: str | None = None


def format_money(amount: Decimal) -> str:
    """Vietnamese-style thousands separator; VND has no subunit worth printing."""
    return f"{int(amount):,}".replace(",", ".")


def _payment_label(method: str) -> str:
    return _PAYMENT_LABELS.get(method, method)


def _unicode_font() -> str:
    """Register a Vietnamese-capable TTF once; fall back to Helvetica if absent.

    Base-14 PDF fonts (Helvetica) use WinAnsi encoding, which drops most
    Vietnamese diacritics — the fallback degrades rendering rather than
    crashing. Requires ``fonts-dejavu-core`` (or ``fonts-noto``) on the host;
    this is a deploy-time dependency, not something this code can install.
    """
    global _resolved_font
    if _resolved_font is not None:
        return _resolved_font
    for path in _UNICODE_FONT_CANDIDATES:
        if Path(path).exists():
            pdfmetrics.registerFont(TTFont(_UNICODE_FONT_NAME, path))
            _resolved_font = _UNICODE_FONT_NAME
            return _resolved_font
    _resolved_font = "Helvetica"
    return _resolved_font


def _center(text: str, width: int = K80_WIDTH) -> str:
    return text.center(width).rstrip()


def _rule(char: str = "-", width: int = K80_WIDTH) -> str:
    return char * width


def _two_col(left: str, right: str, width: int = K80_WIDTH) -> str:
    pad = width - len(left) - len(right)
    if pad < 1:
        return f"{left} {right}"
    return f"{left}{' ' * pad}{right}"


def render_thermal_k80(receipt: ReceiptSummaryDTO, org: OrgSettings) -> str:
    """Plain monospace text sized for an 80mm/Font-A printer (48 columns)."""
    out: list[str] = [_center(org.pharmacy_name)]
    if org.address:
        out.append(_center(org.address))
    if org.phone:
        out.append(_center(f"ĐT: {org.phone}"))
    if org.tax_code:
        out.append(_center(f"MST: {org.tax_code}"))
    out.append(_rule("="))
    out.append(f"Mã đơn: {receipt.order_id}")
    out.append(f"Ngày: {receipt.created_at.strftime('%d/%m/%Y %H:%M')}")
    out.append(_rule())
    for item in receipt.lines:
        out.append(item.name[:K80_WIDTH])
        detail = f"  {item.quantity} {item.unit} x {format_money(item.unit_price)}"
        out.append(_two_col(detail, format_money(item.line_total)))
    out.append(_rule())
    out.append(_two_col("Tổng cộng:", format_money(receipt.subtotal)))
    for payment in receipt.payments:
        label = f"{_payment_label(payment.method.value)}:"
        out.append(_two_col(label, format_money(payment.amount)))
    if receipt.change_amount > 0:
        out.append(_two_col("Tiền thối:", format_money(receipt.change_amount)))
    out.append(_rule("="))
    out.append(_center("Cảm ơn quý khách!"))
    out.append("")
    out.append("Ký tên: " + "_" * (K80_WIDTH - 8))
    out.append(_rule("="))
    return "\n".join(out) + "\n"


def render_pdf(
    receipt: ReceiptSummaryDTO, org: OrgSettings, page_size: Literal["A5", "A4"] = "A5"
) -> bytes:
    """A5/A4 PDF of the same content as :func:`render_thermal_k80`."""
    size = A5 if page_size == "A5" else A4
    width, height = size
    font = _unicode_font()
    buf = BytesIO()
    canvas = Canvas(buf, pagesize=size)
    margin = 12 * mm
    y = height - margin

    def line(text: str, *, size_pt: float = 10, center: bool = False) -> None:
        nonlocal y
        canvas.setFont(font, size_pt)
        if center:
            canvas.drawCentredString(width / 2, y, text)
        else:
            canvas.drawString(margin, y, text)
        y -= size_pt + 4

    def two_col(left: str, right: str, size_pt: float = 10) -> None:
        nonlocal y
        canvas.setFont(font, size_pt)
        canvas.drawString(margin, y, left)
        canvas.drawRightString(width - margin, y, right)
        y -= size_pt + 4

    def rule() -> None:
        nonlocal y
        canvas.line(margin, y, width - margin, y)
        y -= 8

    line(org.pharmacy_name, size_pt=13, center=True)
    if org.address:
        line(org.address, size_pt=9, center=True)
    if org.phone:
        line(f"ĐT: {org.phone}", size_pt=9, center=True)
    if org.tax_code:
        line(f"MST: {org.tax_code}", size_pt=9, center=True)
    rule()
    line(f"Mã đơn: {receipt.order_id}")
    line(f"Ngày: {receipt.created_at.strftime('%d/%m/%Y %H:%M')}")
    rule()
    for item in receipt.lines:
        line(item.name)
        two_col(
            f"  {item.quantity} {item.unit} x {format_money(item.unit_price)}",
            format_money(item.line_total),
        )
    rule()
    two_col("Tổng cộng:", format_money(receipt.subtotal), size_pt=11)
    for payment in receipt.payments:
        two_col(f"{_payment_label(payment.method.value)}:", format_money(payment.amount))
    if receipt.change_amount > 0:
        two_col("Tiền thối:", format_money(receipt.change_amount))
    rule()
    line("Cảm ơn quý khách!", center=True)
    y -= 16
    line("Ký tên:", size_pt=9)
    y -= 20
    canvas.line(margin, y, margin + 60 * mm, y)

    canvas.showPage()
    canvas.save()
    return buf.getvalue()
