"""Compose the procurement module: build its service and router."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.di import Container
from pharmacy_os.core.events import EventBus
from pharmacy_os.modules.procurement.application import ProcurementService
from pharmacy_os.modules.procurement.infrastructure import (
    SqlAlchemyGoodsReceiptRepository,
    SqlAlchemyPurchaseOrderRepository,
    SqlAlchemySupplierRepository,
)
from pharmacy_os.modules.procurement.interface.router import ContextDep, build_router


def register(container: Container, get_context: ContextDep) -> APIRouter:
    session_factory = container.resolve(async_sessionmaker[AsyncSession])
    event_bus = container.resolve(EventBus)  # type: ignore[type-abstract]

    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    def supplier_repo_factory(uow: UnitOfWork, ctx: RequestContext) -> SqlAlchemySupplierRepository:
        return SqlAlchemySupplierRepository(uow.session, ctx)

    def po_repo_factory(uow: UnitOfWork, ctx: RequestContext) -> SqlAlchemyPurchaseOrderRepository:
        return SqlAlchemyPurchaseOrderRepository(uow.session, ctx)

    def grn_repo_factory(uow: UnitOfWork, ctx: RequestContext) -> SqlAlchemyGoodsReceiptRepository:
        return SqlAlchemyGoodsReceiptRepository(uow.session, ctx)

    service = ProcurementService(
        uow_factory, supplier_repo_factory, po_repo_factory, grn_repo_factory
    )
    container.register_instance(ProcurementService, service)
    return build_router(get_context)
