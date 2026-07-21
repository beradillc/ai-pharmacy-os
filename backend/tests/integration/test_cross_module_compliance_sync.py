"""C.5 cross-module: a ``SaleCompleted`` enqueues a national-DB sync push.

The subscription is declared at the composition root (``wire_compliance_sync``),
same pattern as ``wire_sale_dispensing``. Compliance never imports sales — it only
reacts to the already-published event and drives its own ``NationalSyncService``.

Scope note (design 5a): this link only enqueues a ``NationalSyncLog``. It does NOT
write a ``ControlledLedgerEntry`` — ``SaleCompleted`` carries none of the legally
required category/lot/customer/prescription fields, so the ledger stays an explicit
use-case (``record_controlled_entry``).
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.api.v1.compliance_cross import wire_compliance_sync
from pharmacy_os.api.v1.national_sync import MockNationalDrugDbGateway
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.di import Container
from pharmacy_os.core.events import EventBus, InMemoryEventBus
from pharmacy_os.modules.compliance.application import NationalSyncService
from pharmacy_os.modules.compliance.domain import SyncPayloadType, SyncStatus
from pharmacy_os.modules.compliance.infrastructure import (
    NationalSyncLogORM,
    SqlAlchemyNationalSyncLogRepository,
)
from pharmacy_os.modules.sales.domain import SaleCompleted, SoldItem


@pytest.fixture
def wired_container(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> Container:
    """A container with the real event bus + sync service, C.5 subscription wired."""

    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    def repo_factory(uow: UnitOfWork, c: RequestContext) -> SqlAlchemyNationalSyncLogRepository:
        return SqlAlchemyNationalSyncLogRepository(uow.session, c)

    service = NationalSyncService(uow_factory, repo_factory, MockNationalDrugDbGateway())

    container = Container()
    container.register_instance(EventBus, event_bus)  # type: ignore[type-abstract]
    container.register_instance(NationalSyncService, service)
    wire_compliance_sync(container)
    return container


def _sale(tenant_id: UUID, *, client_uuid: str) -> SaleCompleted:
    return SaleCompleted(
        tenant_id=tenant_id,
        order_id=uuid4(),
        branch_id=uuid4(),
        client_uuid=client_uuid,
        items=(SoldItem(drug_id=uuid4(), quantity=Decimal("2")),),
    )


async def _count_logs(session_factory: async_sessionmaker[AsyncSession], client_uuid: str) -> int:
    async with session_factory() as session:
        result = await session.execute(
            select(func.count())
            .select_from(NationalSyncLogORM)
            .where(NationalSyncLogORM.client_uuid == client_uuid)
        )
        return int(result.scalar_one())


async def test_sale_completed_enqueues_one_acked_sale_sync(
    wired_container: Container,
    event_bus: InMemoryEventBus,
    session_factory: async_sessionmaker[AsyncSession],
    ctx: RequestContext,
) -> None:
    await event_bus.publish(_sale(ctx.tenant_id, client_uuid="sale-c5-001"))

    assert await _count_logs(session_factory, "sale-c5-001") == 1
    async with session_factory() as session:
        repo = SqlAlchemyNationalSyncLogRepository(session, ctx)
        log = await repo.by_client_uuid("sale-c5-001")
    assert log is not None
    assert log.payload_type is SyncPayloadType.SALE
    assert log.status is SyncStatus.ACK  # reached ACK via the mock gateway
    assert log.payload_hash  # only the hash is persisted, never the raw payload


async def test_resync_same_client_uuid_does_not_duplicate_log(
    wired_container: Container,
    event_bus: InMemoryEventBus,
    session_factory: async_sessionmaker[AsyncSession],
    ctx: RequestContext,
) -> None:
    event = _sale(ctx.tenant_id, client_uuid="sale-c5-dup")
    await event_bus.publish(event)
    await event_bus.publish(event)  # offline re-sync replays the same SaleCompleted

    assert await _count_logs(session_factory, "sale-c5-dup") == 1  # idempotent by client_uuid


async def test_distinct_sales_enqueue_distinct_logs(
    wired_container: Container,
    event_bus: InMemoryEventBus,
    session_factory: async_sessionmaker[AsyncSession],
    ctx: RequestContext,
) -> None:
    await event_bus.publish(_sale(ctx.tenant_id, client_uuid="sale-c5-a"))
    await event_bus.publish(_sale(ctx.tenant_id, client_uuid="sale-c5-b"))

    assert await _count_logs(session_factory, "sale-c5-a") == 1
    assert await _count_logs(session_factory, "sale-c5-b") == 1
