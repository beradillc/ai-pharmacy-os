"""Line-level sales aggregation read (``aggregate_sold_by_drug``) — the port the
analytics module reads to model demand velocity + top sellers (PROJECT_STATE §7am,
Q1). The point under test: net-of-returns quantity, DRAFT excluded, grouped per drug.
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.sales.application import (
    CreateSaleInput,
    PaymentInput,
    RegisterReturnInput,
    SaleLineInput,
    SalesService,
)
from pharmacy_os.modules.sales.domain import PaymentMethod

_TODAY = date.today()
_FROM = _TODAY - timedelta(days=90)
_TO = _TODAY + timedelta(days=1)


def _sale(client_uuid: str, drug_id: object, qty: str, price: str) -> CreateSaleInput:
    return CreateSaleInput(
        client_uuid=client_uuid,
        lines=[
            SaleLineInput(
                drug_id=drug_id,  # type: ignore[arg-type]
                quantity=Decimal(qty),
                unit_price=Decimal(price),
            )
        ],
        payments=[PaymentInput(method=PaymentMethod.CASH, amount=Decimal(qty) * Decimal(price))],
    )


async def test_aggregate_sums_quantity_and_revenue_per_drug(
    sales_service: SalesService, ctx: RequestContext
) -> None:
    drug_a, drug_b = uuid4(), uuid4()
    await sales_service.complete_sale(_sale("a1", drug_a, "2", "10000"), ctx)
    await sales_service.complete_sale(_sale("a2", drug_a, "3", "10000"), ctx)
    await sales_service.complete_sale(_sale("b1", drug_b, "1", "50000"), ctx)

    rows = await sales_service.aggregate_sold_by_drug(ctx, date_from=_FROM, date_to=_TO)
    by_drug = {r.drug_id: r for r in rows}

    assert by_drug[drug_a].quantity_sold == Decimal("5")
    assert by_drug[drug_a].revenue == Decimal("50000")
    assert by_drug[drug_b].quantity_sold == Decimal("1")
    assert by_drug[drug_b].revenue == Decimal("50000")
    assert all(r.branch_id == ctx.branch_id for r in rows)


async def test_aggregate_is_net_of_returns(
    sales_service: SalesService, ctx: RequestContext
) -> None:
    drug = uuid4()
    out = await sales_service.complete_sale(_sale("r1", drug, "5", "10000"), ctx)
    line_id = out.lines[0].id
    await sales_service.register_return(
        out.id, RegisterReturnInput(line_id=line_id, quantity=Decimal("2")), ctx
    )

    rows = await sales_service.aggregate_sold_by_drug(ctx, date_from=_FROM, date_to=_TO)
    row = next(r for r in rows if r.drug_id == drug)
    assert row.quantity_sold == Decimal("3")  # 5 sold − 2 returned
    assert row.revenue == Decimal("30000")


async def test_fully_returned_drug_is_excluded(
    sales_service: SalesService, ctx: RequestContext
) -> None:
    drug = uuid4()
    out = await sales_service.complete_sale(_sale("f1", drug, "4", "10000"), ctx)
    await sales_service.register_return(
        out.id,
        RegisterReturnInput(line_id=out.lines[0].id, quantity=Decimal("4")),
        ctx,
    )

    rows = await sales_service.aggregate_sold_by_drug(ctx, date_from=_FROM, date_to=_TO)
    assert all(r.drug_id != drug for r in rows)  # net 0 → dropped


async def test_branch_filter_narrows(sales_service: SalesService, ctx: RequestContext) -> None:
    drug = uuid4()
    await sales_service.complete_sale(_sale("x1", drug, "2", "10000"), ctx)

    own = await sales_service.aggregate_sold_by_drug(
        ctx, date_from=_FROM, date_to=_TO, branch_id=ctx.branch_id
    )
    foreign = await sales_service.aggregate_sold_by_drug(
        ctx, date_from=_FROM, date_to=_TO, branch_id=uuid4()
    )
    assert any(r.drug_id == drug for r in own)
    assert foreign == []
