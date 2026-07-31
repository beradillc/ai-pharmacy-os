"""Compose the inventory module: service, event handlers and router."""

from __future__ import annotations

from fastapi import APIRouter

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.db import UnitOfWorkFactory
from pharmacy_os.core.di import Container
from pharmacy_os.core.events import EventBus
from pharmacy_os.modules.inventory.application import InventoryService
from pharmacy_os.modules.inventory.domain import (
    LocationInfoProvider,
    LowStockDetected,
    StockMovedIn,
    StockMovedOut,
)
from pharmacy_os.modules.inventory.infrastructure import (
    SqlAlchemyBalanceRepository,
    SqlAlchemyBatchRepository,
    SqlAlchemyMovementRepository,
    SqlAlchemyStockAtLocationRepository,
    SqlAlchemyStockCountRepository,
    SqlAlchemyStockReconciliationRepository,
)
from pharmacy_os.modules.inventory.interface import handlers
from pharmacy_os.modules.inventory.interface.router import ContextDep, build_router


def register(
    container: Container,
    get_context: ContextDep,
    *,
    locations: LocationInfoProvider | None = None,
) -> APIRouter:
    """``locations`` tuỳ chọn: chưa truyền thì các use-case vị trí trả rỗng hoặc từ chối
    tường minh. Giữ tham số ở dạng tuỳ chọn để mọi bên gọi cũ — kể cả test dựng app bằng
    tay — chạy nguyên vẹn mà không phải sửa."""
    event_bus = container.resolve(EventBus)  # type: ignore[type-abstract]

    uow_factory = container.resolve(UnitOfWorkFactory)

    service = InventoryService(
        uow_factory,
        lambda uow, ctx: SqlAlchemyBatchRepository(uow.session, ctx),
        lambda uow, ctx: SqlAlchemyMovementRepository(uow.session, ctx),
        lambda uow, ctx: SqlAlchemyBalanceRepository(uow.session, ctx),
        lambda uow, ctx: SqlAlchemyStockReconciliationRepository(uow.session, ctx),
        container.resolve(AuditLogger),
        count_repo_factory=lambda uow, ctx: SqlAlchemyStockCountRepository(uow.session, ctx),
        at_location_repo_factory=lambda uow, ctx: SqlAlchemyStockAtLocationRepository(
            uow.session, ctx
        ),
        locations=locations,
    )
    container.register_instance(InventoryService, service)

    event_bus.subscribe(StockMovedIn, handlers.on_stock_moved_in)
    event_bus.subscribe(StockMovedOut, handlers.on_stock_moved_out)
    event_bus.subscribe(LowStockDetected, handlers.on_low_stock)

    return build_router(get_context)
