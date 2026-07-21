"""API v1 router aggregation.

Builds the versioned router from the health endpoint plus each business
module's router. Module ``register`` functions also wire their services and
event handlers into the container (side effect), so this runs at app startup.
"""

from __future__ import annotations

from fastapi import APIRouter

from pharmacy_os.api.deps import get_context
from pharmacy_os.api.v1.cross_module import wire_sale_dispensing
from pharmacy_os.api.v1.health import router as health_router
from pharmacy_os.core.di import Container
from pharmacy_os.modules.catalog.interface import register as register_catalog
from pharmacy_os.modules.inventory.interface import register as register_inventory
from pharmacy_os.modules.sales.interface import register as register_sales


def build_api_router(container: Container) -> APIRouter:
    api = APIRouter(prefix="/api/v1")
    api.include_router(health_router)
    api.include_router(register_catalog(container, get_context))
    api.include_router(register_inventory(container, get_context))
    api.include_router(register_sales(container, get_context))

    # Cross-module reactions (both modules' services now registered).
    wire_sale_dispensing(container)
    return api


__all__ = ["build_api_router"]
