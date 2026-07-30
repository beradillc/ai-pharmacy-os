"""API v1 router aggregation.

Builds the versioned router from the health endpoint plus each business
module's router. Module ``register`` functions also wire their services and
event handlers into the container (side effect), so this runs at app startup.
"""

from __future__ import annotations

from fastapi import APIRouter

from pharmacy_os.api.deps import get_context
from pharmacy_os.api.v1.analytics_wiring import wire_analytics
from pharmacy_os.api.v1.audit import router as audit_router
from pharmacy_os.api.v1.audit_dashboard import router as audit_dashboard_router
from pharmacy_os.api.v1.compliance_cross import wire_compliance_sync
from pharmacy_os.api.v1.cross_module import (
    CatalogDrugInfoProvider,
    CatalogDrugMasterProvider,
    CrmClinicalAllergyRiskProvider,
    IamAuthReauthProvider,
    PrescriptionInfoAdapter,
    SalesLoyaltyAccrualReader,
    wire_goods_receipt_stock_in,
    wire_medication_history,
    wire_safety_checks,
    wire_sale_dispensing,
)
from pharmacy_os.api.v1.health import router as health_router
from pharmacy_os.api.v1.national_sync import wire_national_sync
from pharmacy_os.api.v1.outbox_wiring import wire_outbox
from pharmacy_os.api.v1.privacy import router as privacy_router
from pharmacy_os.api.v1.reports import router as reports_router
from pharmacy_os.core.di import Container
from pharmacy_os.modules.analytics.interface import register as register_analytics
from pharmacy_os.modules.catalog.application import CatalogService
from pharmacy_os.modules.catalog.interface import register as register_catalog
from pharmacy_os.modules.clinical.application import ClinicalService
from pharmacy_os.modules.clinical.interface import register as register_clinical
from pharmacy_os.modules.compliance.interface import register as register_compliance
from pharmacy_os.modules.crm.application import CrmService
from pharmacy_os.modules.crm.interface import register as register_crm
from pharmacy_os.modules.iam.application import AuthService
from pharmacy_os.modules.iam.interface import register as register_iam
from pharmacy_os.modules.inventory.interface import register as register_inventory
from pharmacy_os.modules.prescription.application import PrescriptionService
from pharmacy_os.modules.prescription.interface import register as register_prescription
from pharmacy_os.modules.procurement.interface import register as register_procurement
from pharmacy_os.modules.sales.application import SalesService
from pharmacy_os.modules.sales.interface import register as register_sales


def build_api_router(container: Container) -> APIRouter:
    api = APIRouter(prefix="/api/v1")
    api.include_router(health_router)
    # Iam first: it owns /auth (public) plus /users and /roles, and every other
    # module's router depends on the context its tokens carry.
    for iam_router in register_iam(container, get_context):
        api.include_router(iam_router)
    # Audit trail + privacy record: kernel infrastructure, owned by no business module.
    api.include_router(audit_router)
    # Audit dashboard: the Sprint 7 investigation/inspection lens (entity filter + CSV
    # export), guarded by its own audit.dashboard.read permission.
    api.include_router(audit_dashboard_router)
    api.include_router(privacy_router)
    api.include_router(register_catalog(container, get_context))
    api.include_router(register_inventory(container, get_context))
    api.include_router(register_prescription(container, get_context))
    # Clinical: deterministic interaction check + AI-explanation audit (mock LLM).
    api.include_router(register_clinical(container, get_context))
    # Crm: customer/patient records — single-module, no cross-module wiring yet
    # (allergy check against clinical is a later step, gated behind Opus).
    api.include_router(register_crm(container, get_context))
    # Procurement: suppliers/PO/GRN — single-module, no cross-module wiring yet
    # (GRN confirmed -> inventory batch/stock-in is a later step, gated behind Opus).
    api.include_router(register_procurement(container, get_context))

    # National drug DB sync service (mock gateway — BLOCKER: DAV API spec). Wired before
    # the compliance router so its endpoint can resolve the same instance C.5's
    # cross-module subscriber uses further down.
    wire_national_sync(container)
    # Compliance: sổ thuốc kiểm soát đặc biệt + cấu hình tenant + liên thông CSDL Dược.
    # drug_master: first real wiring of a port defined earlier for QĐ540 Bảng 1 but never
    # implemented — reused 2026-07-25 for the Mẫu số 06 periodic report (docs/13 mục C.7).
    # reauth: bước 6 ký sổ điện tử (docs/13 mục C.5, hướng A) — compliance verifies a
    # password it doesn't own via a read-port wrapping iam's AuthService, same shape as
    # drug_master (docs/features/tt18-kiem-soat-dac-biet/02_DECISIONS_KY_SO.md Bước 3).
    drug_master = CatalogDrugMasterProvider(container.resolve(CatalogService))
    reauth = IamAuthReauthProvider(container.resolve(AuthService))
    api.include_router(register_compliance(container, get_context, drug_master, reauth))

    # Catalog is authoritative for a sale's Rx status; prescription for its ref
    # validity (adapters over their services — sales imports neither module).
    drug_info = CatalogDrugInfoProvider(container.resolve(CatalogService))
    # Cổng dị ứng Đ-6: nối lại catalog + crm + clinical, sales không import module nào.
    allergy_risk = CrmClinicalAllergyRiskProvider(
        container.resolve(CatalogService),
        container.resolve(CrmService),
        container.resolve(ClinicalService),
    )
    rx_info = PrescriptionInfoAdapter(container.resolve(PrescriptionService))
    api.include_router(register_sales(container, get_context, drug_info, rx_info, allergy_risk))

    # Cột "Điểm" trên màn Khách hàng: crm đọc tổng đã mua trong năm từ sales. Nối ở ĐÂY,
    # sau khi sales đã dựng — thứ tự đăng ký có vòng (sales cần CrmService cho cổng dị
    # ứng), nên một trong hai phải nối muộn; chọn cái phụ, không chọn cái an toàn.
    container.resolve(CrmService).attach_accrual_reader(
        SalesLoyaltyAccrualReader(container.resolve(SalesService))
    )

    # Sprint 7 report exports (composition root, like the audit dashboard): reads
    # sales + inventory's own report methods, neither module imports the other.
    # No new permission — reuses sales.read/inventory.read (PROJECT_STATE §7am).
    api.include_router(reports_router)

    # Analytics: reorder suggestions + dashboard (composition root, reads
    # sales/inventory/procurement via adapters, writes DRAFT POs via procurement).
    # Wired after those three services are registered (PROJECT_STATE §7am/§7ap).
    wire_analytics(container)
    api.include_router(register_analytics(container, get_context))

    # Cross-module reactions (both modules' services now registered).
    wire_sale_dispensing(container)

    # A confirmed goods-receipt note (procurement) creates inventory batches.
    wire_goods_receipt_stock_in(container)

    # S6 5.5.4: auto-check clinical safety on a completed sale / dispensed Rx
    # (warn-only). Interactions on both (tenant-gated); allergies on dispensing
    # (reads crm for the customer's allergies). Reads catalog for ingredients.
    wire_safety_checks(container)

    # Fold a named customer's dispensed drugs into their CRM medication history
    # (consent-gated, idempotent). Separate from the warn-only safety checks: this
    # one writes to crm. Reads sales/prescription for the customer_id and items.
    wire_medication_history(container)

    # C.5 cross-module reaction: a completed sale enqueues a national-DB sync push
    # (both the event bus and the sync service are now registered).
    wire_compliance_sync(container)

    # Last: the outbox needs every module's event classes to resolve what it stored.
    wire_outbox(container)
    return api


__all__ = ["build_api_router"]
