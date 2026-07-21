"""Catalog is authoritative for a sale's Rx status (DrugInfoProvider override)."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.errors import ValidationError
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.modules.sales.application import (
    CreateSaleInput,
    PaymentInput,
    SaleLineInput,
    SalesService,
)
from pharmacy_os.modules.sales.domain import DrugInfo, PaymentMethod
from pharmacy_os.modules.sales.infrastructure import SqlAlchemySalesRepository


class FakeDrugInfo:
    def __init__(self, rx_by_drug: dict[UUID, bool]) -> None:
        self._rx = rx_by_drug

    async def get(self, drug_id: UUID, tenant_id: UUID) -> DrugInfo | None:
        if drug_id not in self._rx:
            return None
        return DrugInfo(drug_id=drug_id, requires_prescription=self._rx[drug_id])


def _service(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    provider: FakeDrugInfo,
) -> SalesService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return SalesService(
        uow_factory,
        lambda uow, c: SqlAlchemySalesRepository(uow.session, c),
        provider,
    )


def _sale(
    drug_id: UUID, client_uuid: str, *, client_rx: bool, rx_ref: UUID | None = None
) -> CreateSaleInput:
    return CreateSaleInput(
        client_uuid=client_uuid,
        lines=[
            SaleLineInput(
                drug_id=drug_id,
                quantity=Decimal("1"),
                unit_price=Decimal("10000"),
                requires_prescription=client_rx,
            )
        ],
        payments=[PaymentInput(method=PaymentMethod.CASH, amount=Decimal("10000"))],
        prescription_ref=rx_ref,
    )


async def test_catalog_forces_rx_even_if_client_says_otc(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    etc = uuid4()
    svc = _service(session_factory, event_bus, FakeDrugInfo({etc: True}))
    # Client mislabels an ETC drug as OTC and sends no prescription — must fail.
    with pytest.raises(ValidationError):
        await svc.complete_sale(_sale(etc, "lie-1", client_rx=False), ctx)


async def test_catalog_forces_otc_even_if_client_says_rx(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    otc = uuid4()
    svc = _service(session_factory, event_bus, FakeDrugInfo({otc: False}))
    # Catalog says OTC, so the sale succeeds without a prescription ref.
    out = await svc.complete_sale(_sale(otc, "otc-1", client_rx=True), ctx)
    assert out.status == "COMPLETED"


async def test_unknown_drug_falls_back_to_client_flag(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    unknown = uuid4()
    svc = _service(session_factory, event_bus, FakeDrugInfo({}))
    with pytest.raises(ValidationError):
        await svc.complete_sale(_sale(unknown, "unk-1", client_rx=True), ctx)
