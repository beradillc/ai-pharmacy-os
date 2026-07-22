"""API v1 router aggregation.

Builds the versioned router from the health endpoint plus each business
module's router. Module ``register`` functions also wire their services and
event handlers into the container (side effect), so this runs at app startup.
"""

from __future__ import annotations

from fastapi import APIRouter

from pharmacy_os.api.deps import get_context
from pharmacy_os.api.v1.compliance_cross import wire_compliance_sync
from pharmacy_os.api.v1.cross_module import (
    CatalogDrugInfoProvider,
    PrescriptionInfoAdapter,
    wire_interaction_safety_check,
    wire_sale_dispensing,
)
from pharmacy_os.api.v1.health import router as health_router
from pharmacy_os.api.v1.national_sync import wire_national_sync
from pharmacy_os.core.di import Container
from pharmacy_os.modules.catalog.application import CatalogService
from pharmacy_os.modules.catalog.interface import register as register_catalog
from pharmacy_os.modules.clinical.interface import register as register_clinical
from pharmacy_os.modules.crm.interface import register as register_crm
from pharmacy_os.modules.inventory.interface import register as register_inventory
from pharmacy_os.modules.prescription.application import PrescriptionService
from pharmacy_os.modules.prescription.interface import register as register_prescription
from pharmacy_os.modules.sales.interface import register as register_sales


def build_api_router(container: Container) -> APIRouter:
    api = APIRouter(prefix="/api/v1")
    api.include_router(health_router)
    api.include_router(register_catalog(container, get_context))
    api.include_router(register_inventory(container, get_context))
    api.include_router(register_prescription(container, get_context))
    # Clinical: deterministic interaction check + AI-explanation audit (mock LLM).
    api.include_router(register_clinical(container, get_context))
    # Crm: customer/patient records — single-module, no cross-module wiring yet
    # (allergy check against clinical is a later step, gated behind Opus).
    api.include_router(register_crm(container, get_context))

    # Catalog is authoritative for a sale's Rx status; prescription for its ref
    # validity (adapters over their services — sales imports neither module).
    drug_info = CatalogDrugInfoProvider(container.resolve(CatalogService))
    rx_info = PrescriptionInfoAdapter(container.resolve(PrescriptionService))
    api.include_router(register_sales(container, get_context, drug_info, rx_info))

    # Cross-module reactions (both modules' services now registered).
    wire_sale_dispensing(container)

    # S6 5.5.4: auto-check drug interactions on a completed sale / dispensed Rx
    # (warn-only, tenant-gated). Reads catalog for ingredients + drives clinical.
    wire_interaction_safety_check(container)

    # National drug DB sync service (mock gateway — BLOCKER: DAV API spec).
    # Registered here so C.5's cross-module subscriber can resolve it; no router.
    wire_national_sync(container)

    # C.5 cross-module reaction: a completed sale enqueues a national-DB sync push
    # (both the event bus and the sync service are now registered).
    wire_compliance_sync(container)
    return api


__all__ = ["build_api_router"]
