"""Danh sách hoá đơn (``SalesService.list_sales``) — cổng đọc cho màn Hoá đơn
(Sprint 10, D1).

Điều đang được canh, theo thứ tự quan trọng:

1. **Đơn nhiều hình thức thanh toán không bị thổi phồng.** Đây là lý do repo gộp
   lines và payments bằng hai subquery riêng thay vì hai join. Một đơn 2 dòng ×
   2 lần trả tiền mà join cả hai sẽ ra 4 hàng ⇒ subtotal gấp đôi, paid_total gấp
   đôi. Test ``test_multi_tender_order_is_not_inflated`` là cái duy nhất ở đây
   phân biệt được bản cài đặt đúng với bản sai — và nó ĐÃ ĐƯỢC XEM ĐỎ vì đúng lý
   do (kỷ luật #14): thay hai subquery bằng hai join thì nó đỏ với
   ``subtotal 240000 != 120000``, khôi phục thì xanh lại.
2. Sắp xếp mới-trước (danh sách quầy đọc ngược, khác báo cáo doanh thu).
3. Nháp có mặt và mang đúng ``status`` — khác ``revenue_report_rows``.
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import PermissionDeniedError, ValidationError
from pharmacy_os.modules.sales.application import (
    CreateSaleInput,
    PaymentInput,
    SaleLineInput,
    SalesService,
)
from pharmacy_os.modules.sales.domain import PaymentMethod

#: 🔴 Biên trên phải là NGÀY MAI, không phải hôm nay.
#:
#: Hai mốc này tính lúc **import module**, còn ``created_at`` của đơn do CSDL đặt lúc
#: **chạy test**. Một lượt `pytest` đủ dài chạy qua nửa đêm thì đơn mang ngày hôm sau,
#: bộ lọc mang ngày hôm trước, và 4 test cùng đỏ với `assert 0 == 3` — trông y hệt lỗi
#: phân trang. Đã xảy ra thật lúc 00:02 ngày 31/07/2026: chạy riêng thì xanh, chạy cả bộ
#: thì đỏ. Nới biên trên một ngày là đủ, và không làm yếu phép kiểm nào ở đây: không test
#: nào trong file này canh việc loại bỏ đơn ở tương lai.
_TODAY = date.today()
_DEN = _TODAY + timedelta(days=1)
_FROM = _TODAY - timedelta(days=7)


def _sale(client_uuid: str, *lines: tuple[str, str], tenders: list[str] | None = None):
    """Đơn với các dòng ``(qty, price)``; ``tenders`` là các lần trả tiền rời."""
    total = sum(Decimal(q) * Decimal(p) for q, p in lines)
    amounts = [Decimal(t) for t in tenders] if tenders else [total]
    return CreateSaleInput(
        client_uuid=client_uuid,
        lines=[
            SaleLineInput(drug_id=uuid4(), quantity=Decimal(q), unit_price=Decimal(p))
            for q, p in lines
        ],
        payments=[PaymentInput(method=PaymentMethod.CASH, amount=a) for a in amounts],
    )


async def test_multi_tender_order_is_not_inflated(
    sales_service: SalesService, ctx: RequestContext
) -> None:
    """2 dòng × 2 lần trả tiền: hàng phải là MỘT, tiền phải là thật."""
    await sales_service.complete_sale(
        _sale("mt1", ("2", "30000"), ("1", "60000"), tenders=["50000", "70000"]), ctx
    )

    rows = await sales_service.list_sales(ctx, date_from=_FROM, date_to=_DEN)

    assert len(rows) == 1
    row = rows[0]
    assert row.subtotal == Decimal("120000")  # 2×30000 + 1×60000, KHÔNG phải 240000
    assert row.paid_total == Decimal("120000")  # 50000 + 70000, KHÔNG phải 240000
    assert row.line_count == 2
    # Hình dạng tiền: 2 chữ số thập phân, không phải 5 (lượng 3dp × giá 2dp).
    assert str(row.subtotal) == "120000.00"


async def test_newest_first(sales_service: SalesService, ctx: RequestContext) -> None:
    """Khẳng định BẤT BIẾN thứ tự, không khẳng định một cặp cụ thể.

    ``created_at`` là ``server_default=now()``; trên SQLite ``now()`` chỉ có độ
    phân giải **1 giây**, nên ba đơn tạo liền nhau mang y hệt một mốc thời gian và
    "đơn sau phải đứng trước đơn trước" là một phép tung đồng xu — đúng cái bẫy
    §7bu đã bắt được ở test ``full_name``. Chuỗi không-tăng theo
    ``(created_at, order_id)`` mới là hợp đồng thật của ``ORDER BY … DESC``, và
    nó vẫn có răng: đổi sang ASC là đỏ (đã đo, kỷ luật #14).
    """
    for i in range(3):
        await sales_service.complete_sale(_sale(f"n{i}", ("1", "10000")), ctx)

    rows = await sales_service.list_sales(ctx, date_from=_FROM, date_to=_DEN)
    keys = [(r.created_at, r.order_id) for r in rows]

    assert len(keys) == 3
    assert keys == sorted(keys, reverse=True)


async def test_row_carries_status_and_owner(
    sales_service: SalesService, ctx: RequestContext
) -> None:
    out = await sales_service.complete_sale(_sale("s1", ("3", "15000")), ctx)

    row = next(
        r
        for r in await sales_service.list_sales(ctx, date_from=_FROM, date_to=_DEN)
        if r.order_id == out.id
    )

    assert row.status == out.status
    assert row.branch_id == ctx.branch_id
    assert row.currency == "VND"
    assert row.sold_by_user_id == ctx.user_id


async def test_paging_and_branch_filter(sales_service: SalesService, ctx: RequestContext) -> None:
    for i in range(3):
        await sales_service.complete_sale(_sale(f"p{i}", ("1", "10000")), ctx)

    page = await sales_service.list_sales(ctx, date_from=_FROM, date_to=_DEN, limit=2)
    rest = await sales_service.list_sales(ctx, date_from=_FROM, date_to=_DEN, limit=2, offset=2)
    other_branch = await sales_service.list_sales(
        ctx, date_from=_FROM, date_to=_DEN, branch_id=uuid4()
    )

    assert len(page) == 2
    assert len(rest) == 1
    assert {r.order_id for r in page}.isdisjoint({r.order_id for r in rest})
    assert other_branch == []


async def test_requires_sales_read(sales_service: SalesService, ctx: RequestContext) -> None:
    blind = RequestContext(
        tenant_id=ctx.tenant_id,
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=frozenset({"sales.create"}),
    )

    with pytest.raises(PermissionDeniedError):
        await sales_service.list_sales(blind, date_from=_FROM, date_to=_DEN)


async def test_reversed_range_is_rejected(sales_service: SalesService, ctx: RequestContext) -> None:
    with pytest.raises(ValidationError):
        await sales_service.list_sales(ctx, date_from=_TODAY, date_to=_FROM)
