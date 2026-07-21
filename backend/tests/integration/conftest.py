"""Integration fixtures: a real (SQLite in-memory) DB and wired services."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.models_registry import Base
from pharmacy_os.modules.catalog.application import CatalogService
from pharmacy_os.modules.catalog.infrastructure import SqlAlchemyDrugRepository
from pharmacy_os.modules.compliance.application import ComplianceService
from pharmacy_os.modules.compliance.infrastructure import (
    SqlAlchemyControlledLedgerRepository,
    SqlAlchemyTenantComplianceConfigRepository,
)
from pharmacy_os.modules.inventory.application import InventoryService
from pharmacy_os.modules.inventory.infrastructure import (
    SqlAlchemyBalanceRepository,
    SqlAlchemyBatchRepository,
    SqlAlchemyMovementRepository,
)
from pharmacy_os.modules.prescription.application import PrescriptionService
from pharmacy_os.modules.prescription.infrastructure import SqlAlchemyPrescriptionRepository
from pharmacy_os.modules.sales.application import SalesService
from pharmacy_os.modules.sales.infrastructure import SqlAlchemySalesRepository


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    await engine.dispose()


@pytest.fixture
def event_bus() -> InMemoryEventBus:
    return InMemoryEventBus()


@pytest.fixture
def ctx() -> RequestContext:
    return RequestContext(
        tenant_id=uuid4(),
        branch_id=uuid4(),
        user_id=uuid4(),
        permissions=frozenset(
            {
                "catalog.read",
                "catalog.create",
                "inventory.read",
                "inventory.receive",
                "inventory.dispense",
                "sales.read",
                "sales.create",
                "rx.read",
                "rx.create",
                "rx.approve",
                "rx.dispense",
                "compliance.ledger.read",
                "compliance.ledger.write",
                "compliance.config.read",
                "compliance.config.write",
                "compliance.sync.push",
                "compliance.sync.read",
            }
        ),
    )


@pytest.fixture
def catalog_service(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> CatalogService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return CatalogService(
        uow_factory,
        lambda uow, c: SqlAlchemyDrugRepository(uow.session, c),
    )


@pytest.fixture
def inventory_service(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> InventoryService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return InventoryService(
        uow_factory,
        lambda uow, c: SqlAlchemyBatchRepository(uow.session, c),
        lambda uow, c: SqlAlchemyMovementRepository(uow.session, c),
        lambda uow, c: SqlAlchemyBalanceRepository(uow.session, c),
    )


@pytest.fixture
def sales_service(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> SalesService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return SalesService(
        uow_factory,
        lambda uow, c: SqlAlchemySalesRepository(uow.session, c),
    )


@pytest.fixture
def prescription_service(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> PrescriptionService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return PrescriptionService(
        uow_factory,
        lambda uow, c: SqlAlchemyPrescriptionRepository(uow.session, c),
    )


@pytest.fixture
def compliance_service(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> ComplianceService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return ComplianceService(
        uow_factory,
        lambda uow, c: SqlAlchemyControlledLedgerRepository(uow.session, c),
        lambda uow, c: SqlAlchemyTenantComplianceConfigRepository(uow.session, c),
    )
