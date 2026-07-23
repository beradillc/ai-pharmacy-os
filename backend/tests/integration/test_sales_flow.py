from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.audit import AuditAction, SqlAlchemyAuditLogRepository
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import NotFoundError, ValidationError
from pharmacy_os.core.events import DomainEvent, InMemoryEventBus
from pharmacy_os.modules.sales.application import (
    CreateSaleInput,
    PaymentInput,
    RegisterReturnInput,
    SaleLineInput,
    SalesService,
)
from pharmacy_os.modules.sales.domain import (
    PaymentMethod,
    SaleCompleted,
    SaleReturned,
    SaleStatus,
)


def _sale(client_uuid: str = "c-1", *, rx: bool = False, rx_ref: object = None) -> CreateSaleInput:
    return CreateSaleInput(
        client_uuid=client_uuid,
        lines=[
            SaleLineInput(
                drug_id=uuid4(),
                quantity=Decimal("2"),
                unit_price=Decimal("10000"),
                requires_prescription=rx,
            )
        ],
        payments=[PaymentInput(method=PaymentMethod.CASH, amount=Decimal("20000"))],
        prescription_ref=rx_ref,  # type: ignore[arg-type]
    )


async def test_complete_sale_persists_and_reads_back(
    sales_service: SalesService, ctx: RequestContext
) -> None:
    out = await sales_service.complete_sale(_sale(), ctx)
    assert out.status == SaleStatus.COMPLETED.value
    assert out.subtotal == Decimal("20000.00")

    fetched = await sales_service.get_sale(out.id, ctx)
    assert fetched.id == out.id
    assert len(fetched.lines) == 1


async def test_idempotent_resync_no_duplicate(
    sales_service: SalesService, ctx: RequestContext, event_bus: InMemoryEventBus
) -> None:
    seen: list[str] = []

    async def record(event: DomainEvent) -> None:
        seen.append(event.name)

    event_bus.subscribe(SaleCompleted, record)

    first = await sales_service.complete_sale(_sale("dup-1"), ctx)
    second = await sales_service.complete_sale(_sale("dup-1"), ctx)  # retried sync

    assert second.id == first.id  # same order returned, not a new one
    assert seen == ["SaleCompleted"]  # emitted exactly once


async def test_sale_completed_carries_items(
    sales_service: SalesService, ctx: RequestContext, event_bus: InMemoryEventBus
) -> None:
    captured: list[SaleCompleted] = []

    async def record(event: DomainEvent) -> None:
        assert isinstance(event, SaleCompleted)
        captured.append(event)

    event_bus.subscribe(SaleCompleted, record)
    await sales_service.complete_sale(_sale("evt-1"), ctx)

    assert len(captured) == 1
    assert captured[0].client_uuid == "evt-1"
    assert captured[0].items[0].quantity == Decimal("2")


async def test_underpaid_rejected(sales_service: SalesService, ctx: RequestContext) -> None:
    data = CreateSaleInput(
        client_uuid="under-1",
        lines=[SaleLineInput(drug_id=uuid4(), quantity=Decimal("2"), unit_price=Decimal("10000"))],
        payments=[PaymentInput(method=PaymentMethod.CASH, amount=Decimal("15000"))],
    )
    with pytest.raises(ValidationError):
        await sales_service.complete_sale(data, ctx)


async def test_etc_without_prescription_rejected(
    sales_service: SalesService, ctx: RequestContext
) -> None:
    with pytest.raises(ValidationError):
        await sales_service.complete_sale(_sale("etc-1", rx=True), ctx)


async def test_etc_with_prescription_ref_allowed(
    sales_service: SalesService, ctx: RequestContext
) -> None:
    out = await sales_service.complete_sale(_sale("etc-2", rx=True, rx_ref=uuid4()), ctx)
    assert out.status == SaleStatus.COMPLETED.value


async def test_get_unknown_sale_raises(sales_service: SalesService, ctx: RequestContext) -> None:
    with pytest.raises(NotFoundError):
        await sales_service.get_sale(uuid4(), ctx)


# --- audit trail: the fact an inspection asks about ("ai đã bán thuốc này") ----


async def test_complete_sale_leaves_an_audit_row(
    sales_service: SalesService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Does not trust the call sites to be wired — reads the table back."""
    out = await sales_service.complete_sale(_sale("audit-1"), ctx)

    async with session_factory() as session:
        repo = SqlAlchemyAuditLogRepository(session)
        entries = await repo.list(ctx.tenant_id, action=AuditAction.SALE_COMPLETED)
        matching = [e for e in entries if e.target_id == str(out.id)]
        assert len(matching) == 1
        assert matching[0].actor_user_id == ctx.user_id


async def test_idempotent_resync_leaves_a_single_audit_row(
    sales_service: SalesService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first = await sales_service.complete_sale(_sale("audit-dup"), ctx)
    await sales_service.complete_sale(_sale("audit-dup"), ctx)  # retried sync

    async with session_factory() as session:
        repo = SqlAlchemyAuditLogRepository(session)
        entries = await repo.list(ctx.tenant_id, action=AuditAction.SALE_COMPLETED)
        matching = [e for e in entries if e.target_id == str(first.id)]
        assert len(matching) == 1


# --- returns: đã có domain từ Sprint 4, giờ nối use-case + audit --------------


async def test_register_return_partial_then_full(
    sales_service: SalesService, ctx: RequestContext
) -> None:
    sale = await sales_service.complete_sale(_sale("return-1"), ctx)
    line_id = sale.lines[0].id

    partial = await sales_service.register_return(
        sale.id, RegisterReturnInput(line_id=line_id, quantity=Decimal("1")), ctx
    )
    assert partial.status == SaleStatus.PARTIALLY_RETURNED.value
    assert partial.lines[0].returned_quantity == Decimal("1")

    full = await sales_service.register_return(
        sale.id, RegisterReturnInput(line_id=line_id, quantity=Decimal("1")), ctx
    )
    assert full.status == SaleStatus.RETURNED.value


async def test_register_return_over_quantity_rejected(
    sales_service: SalesService, ctx: RequestContext
) -> None:
    sale = await sales_service.complete_sale(_sale("return-2"), ctx)
    with pytest.raises(ValidationError):
        await sales_service.register_return(
            sale.id,
            RegisterReturnInput(line_id=sale.lines[0].id, quantity=Decimal("999")),
            ctx,
        )


async def test_register_return_unknown_order_raises(
    sales_service: SalesService, ctx: RequestContext
) -> None:
    with pytest.raises(NotFoundError):
        await sales_service.register_return(
            uuid4(), RegisterReturnInput(line_id=uuid4(), quantity=Decimal("1")), ctx
        )


async def test_register_return_emits_event_and_leaves_an_audit_row(
    sales_service: SalesService,
    ctx: RequestContext,
    event_bus: InMemoryEventBus,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Does not trust the call sites to be wired — reads the table back."""
    events: list[SaleReturned] = []

    async def record(event: DomainEvent) -> None:
        assert isinstance(event, SaleReturned)
        events.append(event)

    event_bus.subscribe(SaleReturned, record)

    sale = await sales_service.complete_sale(_sale("return-3"), ctx)
    line_id = sale.lines[0].id
    await sales_service.register_return(
        sale.id, RegisterReturnInput(line_id=line_id, quantity=Decimal("1")), ctx
    )

    assert len(events) == 1
    assert events[0].order_id == sale.id
    assert events[0].line_id == line_id
    assert events[0].quantity == Decimal("1")

    async with session_factory() as session:
        repo = SqlAlchemyAuditLogRepository(session)
        entries = await repo.list(ctx.tenant_id, action=AuditAction.SALE_RETURN_REGISTERED)
        matching = [e for e in entries if e.target_id == str(sale.id)]
        assert len(matching) == 1
        assert matching[0].actor_user_id == ctx.user_id
