"""Compose the inventory module: service, event handlers and router."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.di import Container
from pharmacy_os.core.events import EventBus
from pharmacy_os.modules.inventory.application import InventoryService
from pharmacy_os.modules.inventory.domain import LowStockDetected, StockMovedIn, StockMovedOut
from pharmacy_os.modules.inventory.infrastructure import (
    SqlAlchemyBalanceRepository,
    SqlAlchemyBatchRepository,
    SqlAlchemyMovementRepository,
    SqlAlchemyStockReconciliationRepository,
)
from pharmacy_os.modules.inventory.interface import handlers
from pharmacy_os.modules.inventory.interface.router import ContextDep, build_router


def register(container: Container, get_context: ContextDep) -> APIRouter:
    session_factory = container.resolve(async_sessionmaker[AsyncSession])
    event_bus = container.resolve(EventBus)  # type: ignore[type-abstract]

    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    service = InventoryService(
        uow_factory,
        lambda uow, ctx: SqlAlchemyBatchRepository(uow.session, ctx),
        lambda uow, ctx: SqlAlchemyMovementRepository(uow.session, ctx),
        lambda uow, ctx: SqlAlchemyBalanceRepository(uow.session, ctx),
        lambda uow, ctx: SqlAlchemyStockReconciliationRepository(uow.session, ctx),
    )
    container.register_instance(InventoryService, service)

    event_bus.subscribe(StockMovedIn, handlers.on_stock_moved_in)
    event_bus.subscribe(StockMovedOut, handlers.on_stock_moved_out)
    event_bus.subscribe(LowStockDetected, handlers.on_low_stock)

    return build_router(get_context)
