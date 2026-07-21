"""S5.4 cross-module: sales verifies prescription_ref via the read-port.

Drives ``SalesService.complete_sale`` with a stub ``PrescriptionInfoProvider`` (the
composition root's real adapter is exercised by the app-level e2e). Confirms an ETC
sale is authorised only by a real prescription in a sale-authorising state, while a
provider-less service keeps the old ref-present-only behaviour.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.errors import ValidationError
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.modules.sales.application import SalesService
from pharmacy_os.modules.sales.application.dto import (
    CreateSaleInput,
    PaymentInput,
    SaleLineInput,
)
from pharmacy_os.modules.sales.domain import PaymentMethod, PrescriptionInfo
from pharmacy_os.modules.sales.infrastructure import SqlAlchemySalesRepository


class _StubRxProvider:
    """Returns a fixed status for any prescription_ref, or None (unknown)."""

    def __init__(self, status: str | None) -> None:
        self._status = status
        self.calls: list[tuple[UUID, UUID]] = []

    async def get(self, prescription_id: UUID, tenant_id: UUID) -> PrescriptionInfo | None:
        self.calls.append((prescription_id, tenant_id))
        if self._status is None:
            return None
        return PrescriptionInfo(prescription_id=prescription_id, status=self._status)


def _service(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    provider: _StubRxProvider | None,
) -> SalesService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return SalesService(
        uow_factory,
        lambda uow, c: SqlAlchemySalesRepository(uow.session, c),
        None,  # drug_info: rely on the client rx flag in these tests
        provider,
    )


def _sale(client_uuid: str, *, rx: bool, rx_ref: UUID | None) -> CreateSaleInput:
    return CreateSaleInput(
        client_uuid=client_uuid,
        lines=[
            SaleLineInput(
                drug_id=uuid4(),
                quantity=Decimal("1"),
                unit_price=Decimal("10000"),
                requires_prescription=rx,
            )
        ],
        payments=[PaymentInput(method=PaymentMethod.CASH, amount=Decimal("10000"))],
        prescription_ref=rx_ref,
    )


@pytest.mark.parametrize("status", ["VALIDATED", "DISPENSED"])
async def test_etc_sale_allowed_for_authorising_prescription(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
    status: str,
) -> None:
    provider = _StubRxProvider(status)
    service = _service(session_factory, event_bus, provider)
    out = await service.complete_sale(_sale("ok", rx=True, rx_ref=uuid4()), ctx)
    assert out.status == "COMPLETED"
    assert provider.calls  # the ref was actually verified through the port


@pytest.mark.parametrize("status", ["DRAFT", "REJECTED"])
async def test_etc_sale_blocked_for_non_authorising_prescription(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
    status: str,
) -> None:
    service = _service(session_factory, event_bus, _StubRxProvider(status))
    with pytest.raises(ValidationError):
        await service.complete_sale(_sale("bad", rx=True, rx_ref=uuid4()), ctx)


async def test_etc_sale_blocked_for_unknown_ref(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    service = _service(session_factory, event_bus, _StubRxProvider(None))  # ref not found
    with pytest.raises(ValidationError):
        await service.complete_sale(_sale("ghost", rx=True, rx_ref=uuid4()), ctx)


async def test_otc_sale_skips_prescription_verification(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    provider = _StubRxProvider("REJECTED")  # would block if consulted
    service = _service(session_factory, event_bus, provider)
    out = await service.complete_sale(_sale("otc", rx=False, rx_ref=uuid4()), ctx)
    assert out.status == "COMPLETED"
    assert not provider.calls  # no ETC line → the port is never consulted


async def test_no_provider_keeps_ref_present_only_rule(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    service = _service(session_factory, event_bus, None)  # provider not wired
    out = await service.complete_sale(_sale("legacy", rx=True, rx_ref=uuid4()), ctx)
    assert out.status == "COMPLETED"  # any ref accepted when no provider is configured
