"""``SalesService.get_receipt`` — printable projection for In bill (S7)."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.errors import NotFoundError
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.modules.sales.application import (
    CreateSaleInput,
    PaymentInput,
    SaleLineInput,
    SalesService,
)
from pharmacy_os.modules.sales.domain import DrugInfo, PaymentMethod
from pharmacy_os.modules.sales.infrastructure import SqlAlchemySalesRepository


class FakeDrugDisplay:
    def __init__(self, display_by_drug: dict[UUID, tuple[str, str]]) -> None:
        self._display = display_by_drug

    async def get(self, drug_id: UUID, tenant_id: UUID) -> DrugInfo | None:
        if drug_id not in self._display:
            return None
        name, unit = self._display[drug_id]
        return DrugInfo(drug_id=drug_id, requires_prescription=False, name=name, unit=unit)


def _service(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    provider: FakeDrugDisplay | None,
) -> SalesService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return SalesService(
        uow_factory,
        lambda uow, c: SqlAlchemySalesRepository(uow.session, c),
        provider,
    )


async def test_get_receipt_resolves_display_and_computes_change(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    drug = uuid4()
    display = FakeDrugDisplay({drug: ("Paracetamol 500mg", "viên")})
    svc = _service(session_factory, event_bus, display)
    sale = await svc.complete_sale(
        CreateSaleInput(
            client_uuid="receipt-1",
            lines=[SaleLineInput(drug_id=drug, quantity=Decimal("2"), unit_price=Decimal("10000"))],
            # Cash tender exceeds the 20000 subtotal — customer gets 5000 back.
            payments=[PaymentInput(method=PaymentMethod.CASH, amount=Decimal("25000"))],
        ),
        ctx,
    )

    receipt = await svc.get_receipt(sale.id, ctx)

    assert receipt.order_id == sale.id
    assert receipt.subtotal == Decimal("20000")
    assert receipt.paid_total == Decimal("25000")
    assert receipt.change_amount == Decimal("5000")
    assert len(receipt.lines) == 1
    line = receipt.lines[0]
    assert line.name == "Paracetamol 500mg"
    assert line.unit == "viên"
    assert line.line_total == Decimal("20000")
    assert len(receipt.payments) == 1
    assert receipt.payments[0].method == PaymentMethod.CASH


async def test_get_receipt_unknown_drug_falls_back_to_id(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    drug = uuid4()
    svc = _service(session_factory, event_bus, FakeDrugDisplay({}))
    sale = await svc.complete_sale(
        CreateSaleInput(
            client_uuid="receipt-2",
            lines=[SaleLineInput(drug_id=drug, quantity=Decimal("1"), unit_price=Decimal("5000"))],
            payments=[PaymentInput(method=PaymentMethod.CASH, amount=Decimal("5000"))],
        ),
        ctx,
    )

    receipt = await svc.get_receipt(sale.id, ctx)

    assert receipt.change_amount == Decimal("0")
    assert receipt.lines[0].name == str(drug)
    assert receipt.lines[0].unit == ""


async def test_get_receipt_no_drug_info_provider_falls_back_to_id(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    drug = uuid4()
    svc = _service(session_factory, event_bus, None)
    sale = await svc.complete_sale(
        CreateSaleInput(
            client_uuid="receipt-3",
            lines=[SaleLineInput(drug_id=drug, quantity=Decimal("1"), unit_price=Decimal("5000"))],
            payments=[PaymentInput(method=PaymentMethod.CASH, amount=Decimal("5000"))],
        ),
        ctx,
    )

    receipt = await svc.get_receipt(sale.id, ctx)

    assert receipt.lines[0].name == str(drug)


async def test_get_receipt_unknown_order_raises_not_found(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    svc = _service(session_factory, event_bus, None)
    with pytest.raises(NotFoundError):
        await svc.get_receipt(uuid4(), ctx)
