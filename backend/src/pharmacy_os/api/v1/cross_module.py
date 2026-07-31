"""Cross-module wiring lives here, at the API composition root.

Business modules never import one another (the ``module-independence``
contract). When one module must react to another's event, the subscription is
declared here — the ``api`` layer is allowed to depend on any module. This is
the first such link: a completed sale drives an inventory dispense (FEFO).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import structlog

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.di import Container
from pharmacy_os.core.errors import FeatureDisabledError, NotFoundError
from pharmacy_os.core.events import DomainEvent, EventBus
from pharmacy_os.modules.catalog.application import CatalogService
from pharmacy_os.modules.clinical.application import (
    BasketIngredient,
    CheckAllergiesInput,
    CheckInteractionsInput,
    ClinicalService,
)
from pharmacy_os.modules.clinical.domain import AiContextType
from pharmacy_os.modules.compliance.domain import DrugMasterFacts
from pharmacy_os.modules.compliance.domain.ports import SigningReauthOutcome
from pharmacy_os.modules.crm.application import CrmService, MedicationHistoryItemInput
from pharmacy_os.modules.crm.domain import MedicationHistorySource
from pharmacy_os.modules.iam.application import AuthService, StepUpResult
from pharmacy_os.modules.inventory.application import (
    GoodsReceiptLine,
    InventoryService,
    SaleDispenseItem,
)
from pharmacy_os.modules.prescription.application import PrescriptionService
from pharmacy_os.modules.prescription.domain import PrescriptionDispensed
from pharmacy_os.modules.procurement.domain import GoodsReceived
from pharmacy_os.modules.sales.application import SalesService
from pharmacy_os.modules.sales.domain import (
    AllergyRisk,
    DrugInfo,
    PrescriptionInfo,
    SaleCompleted,
)

_log = structlog.get_logger("cross_module.sales_inventory")

# The dispense is a system reaction (no end-user request), so it runs under a
# fixed system identity holding exactly the inventory permissions it needs.
_SYSTEM_USER = UUID("00000000-0000-0000-0000-00005a1e5001")
_SYSTEM_PERMISSIONS = frozenset({"inventory.read", "inventory.dispense"})

_grn_log = structlog.get_logger("cross_module.goods_receipt_inventory")
# Stock-in from a confirmed GRN needs only the receive right.
_GRN_STOCK_IN_PERMISSIONS = frozenset({"inventory.receive"})

_safety_log = structlog.get_logger("cross_module.safety_checks")

# Same system identity, but the safety checks only read catalog/prescription/crm/
# sales and drive the clinical checks — no inventory rights here. ``sales.read`` lets
# the sale handler resolve the buyer (customer_id) for the OTC allergy check.
_SAFETY_PERMISSIONS = frozenset(
    {"catalog.read", "rx.read", "crm.read", "sales.read", "clinical.check"}
)

_medhist_log = structlog.get_logger("cross_module.medication_history")
# Recording history reads the sale/prescription; the crm write itself is a system
# reaction (record_medication_history is ungated), so only the reads need rights.
_MEDHIST_PERMISSIONS = frozenset({"sales.read", "rx.read"})


def wire_sale_dispensing(container: Container) -> None:
    """Subscribe inventory dispensing to ``SaleCompleted``."""
    event_bus = container.resolve(EventBus)  # type: ignore[type-abstract]
    inventory = container.resolve(InventoryService)

    async def on_sale_completed(event: DomainEvent) -> None:
        assert isinstance(event, SaleCompleted)
        ctx = RequestContext(
            tenant_id=event.tenant_id,
            branch_id=event.branch_id,
            user_id=_SYSTEM_USER,
            permissions=_SYSTEM_PERMISSIONS,
        )
        items = [SaleDispenseItem(drug_id=it.drug_id, quantity=it.quantity) for it in event.items]
        await inventory.dispense_for_sale(items, event.order_id, ctx)
        _log.info("sale_dispensed", order_id=str(event.order_id), lines=len(items))

    event_bus.subscribe(SaleCompleted, on_sale_completed)


def wire_goods_receipt_stock_in(container: Container) -> None:
    """Subscribe inventory stock-in to procurement's ``GoodsReceived``.

    A confirmed goods-receipt note creates one inventory ``ProductBatch`` (+ IN
    movement) per received line, idempotent on ``grn_id``. Lot collisions and any
    other failures are recorded in ``stock_reconciliation_needed`` by the use-case
    rather than blocking — the GRN is already committed. This mirrors
    ``wire_sale_dispensing``; ``procurement`` and ``inventory`` never import each
    other, the link lives here and maps ``ReceivedItem`` onto inventory's own
    ``GoodsReceiptLine``.
    """
    event_bus = container.resolve(EventBus)  # type: ignore[type-abstract]
    inventory = container.resolve(InventoryService)

    async def on_goods_received(event: DomainEvent) -> None:
        assert isinstance(event, GoodsReceived)
        ctx = RequestContext(
            tenant_id=event.tenant_id,
            branch_id=event.branch_id,
            user_id=_SYSTEM_USER,
            permissions=_GRN_STOCK_IN_PERMISSIONS,
        )
        lines = [
            GoodsReceiptLine(
                drug_id=it.drug_id,
                lot_no=it.lot_no,
                expiry_date=it.expiry_date,
                unit_cost=it.unit_cost,
                quantity=it.quantity,
                po_item_id=it.po_item_id,
                mfg_date=it.mfg_date,
            )
            for it in event.items
        ]
        await inventory.receive_from_goods_receipt(lines, event.grn_id, ctx)
        _grn_log.info("grn_stock_in", grn_id=str(event.grn_id), lines=len(lines))

    event_bus.subscribe(GoodsReceived, on_goods_received)


def wire_safety_checks(container: Container) -> None:
    """Subscribe the clinical safety checks to sales and dispensing (warn-only).

    A completed sale (``SaleCompleted``) or dispensed prescription
    (``PrescriptionDispensed``) is resolved to its basket of active ingredients via
    catalog (S6 Bước 1), then run through:

    * **Interactions** (both events) — ``clinical.check_interactions`` over the
      ingredient names; deterministic engine + audited ``AiRecommendation``. Gated
      per-tenant by ``TenantAiSettings`` (default OFF): an unopted tenant raises
      ``FeatureDisabledError``, swallowed silently.
    * **Allergies** (dispensing only — a prescription carries the ``customer_id``) —
      ``clinical.check_allergies`` matching the basket against the customer's recorded
      allergies (read from crm). Deterministic and **not** tenant-gated: it runs for
      every tenant.

    All **warn-only** — both events are post-commit, so the sale/dispense is already
    finalised; blocking-vs-warning is a business/legal call and warn was chosen.
    Handler failures are already isolated by the bus.
    """
    event_bus = container.resolve(EventBus)  # type: ignore[type-abstract]
    clinical = container.resolve(ClinicalService)
    catalog = container.resolve(CatalogService)
    crm = container.resolve(CrmService)
    prescription = container.resolve(PrescriptionService)
    sales = container.resolve(SalesService)

    async def resolve_basket(drug_ids: set[UUID], ctx: RequestContext) -> list[tuple[UUID, str]]:
        """Map the basket's drugs to deduplicated ``(ingredient_id, name)`` pairs."""
        basket: list[tuple[UUID, str]] = []
        seen: set[UUID] = set()
        for drug_id in drug_ids:
            try:
                refs = await catalog.get_drug_ingredients(drug_id, ctx)
            except NotFoundError:
                continue  # a drug absent from catalog can't be checked; skip it
            for ref in refs:
                if ref.ingredient_id not in seen:
                    seen.add(ref.ingredient_id)
                    basket.append((ref.ingredient_id, ref.name))
        return basket

    async def run_interaction_check(
        basket: list[tuple[UUID, str]],
        context_type: AiContextType,
        context_id: UUID,
        ctx: RequestContext,
    ) -> None:
        names = [name for _, name in basket]
        if len({name.strip().casefold() for name in names}) < 2:
            return  # no drug–drug interaction possible; skip to avoid empty audit noise
        # Idempotency key of this reaction: one recommendation per business action.
        # Delivery is at-least-once (transactional outbox), and unlike every other
        # subscriber the interaction check has no natural key of its own — a redelivered
        # event would append a second AiRecommendation + audit row for the same sale,
        # i.e. duplicate the very records an inspection reads as evidence (NĐ356,
        # docs/12). A manual re-check through the API is unaffected: the guard lives
        # here in the automatic handler, not in the use-case.
        if await clinical.find_recommendation_for_context(context_type, context_id, ctx):
            _safety_log.debug(
                "interaction_check_skipped_duplicate",
                context_type=context_type.value,
                context_id=str(context_id),
            )
            return
        try:
            result = await clinical.check_interactions(
                CheckInteractionsInput(
                    ingredients=names, context_type=context_type, context_id=context_id
                ),
                ctx,
            )
        except FeatureDisabledError:
            return  # tenant hasn't opted into clinical AI — a normal state, stay silent
        if result.recommendation.requires_review:
            _safety_log.warning(
                "interaction_warning_raised",
                context_type=context_type.value,
                context_id=str(context_id),
                findings=len(result.findings),
            )

    async def run_allergy_check(
        basket: list[tuple[UUID, str]],
        customer_id: UUID,
        context_id: UUID,
        ctx: RequestContext,
    ) -> None:
        try:
            # A purpose-built read: ingredient ids and severities only, audited as a
            # machine check rather than as somebody opening the patient's file.
            severities = await crm.allergy_severities_for_safety_check(customer_id, ctx)
        except NotFoundError:
            return  # customer record gone; nothing to match against
        if not severities:
            return
        result = await clinical.check_allergies(
            CheckAllergiesInput(
                basket=[BasketIngredient(ingredient_id=i, name=n) for i, n in basket],
                allergy_severities=severities,
                context_id=context_id,
            ),
            ctx,
        )
        if result.alerts:
            _safety_log.warning(
                "allergy_warning_raised",
                context_id=str(context_id),
                customer_id=str(customer_id),
                alerts=len(result.alerts),
            )

    async def on_sale_completed(event: DomainEvent) -> None:
        assert isinstance(event, SaleCompleted)
        ctx = RequestContext(
            tenant_id=event.tenant_id,
            branch_id=event.branch_id,
            user_id=_SYSTEM_USER,
            permissions=_SAFETY_PERMISSIONS,
        )
        basket = await resolve_basket({it.drug_id for it in event.items}, ctx)
        await run_interaction_check(basket, AiContextType.SALE, event.order_id, ctx)
        # A sale may now name its buyer (SalesOrder.customer_id, migration 0016). When
        # it does, the allergy check runs for OTC too — the SaleCompleted contract is
        # unchanged, so the customer_id is read back from the sale, not carried on the
        # event.
        try:
            sale = await sales.get_sale(event.order_id, ctx)
        except NotFoundError:
            return
        if sale.customer_id is not None:
            await run_allergy_check(basket, sale.customer_id, event.order_id, ctx)

    async def on_prescription_dispensed(event: DomainEvent) -> None:
        assert isinstance(event, PrescriptionDispensed)
        # PrescriptionDispensed carries no branch_id; use the tenant as the branch
        # scope (same placeholder the read adapters above use for system reactions).
        ctx = RequestContext(
            tenant_id=event.tenant_id,
            branch_id=event.tenant_id,
            user_id=_SYSTEM_USER,
            permissions=_SAFETY_PERMISSIONS,
        )
        try:
            rx = await prescription.get_prescription(event.prescription_id, ctx)
        except NotFoundError:
            return
        basket = await resolve_basket({it.drug_id for it in rx.items}, ctx)
        await run_interaction_check(basket, AiContextType.RX, event.prescription_id, ctx)
        # 🔴 Không có khách thì KHÔNG có gì để đối chiếu dị ứng: dị ứng là thuộc tính của
        # một người, và `customer_id is None` nghĩa là đơn chụp từ ảnh cho khách không để
        # lại số (Chain chốt 2026-07-31). Kiểm tra tương tác thuốc-thuốc ở dòng trên VẪN
        # chạy — nó chỉ cần giỏ thuốc, không cần biết ai mua.
        if rx.customer_id is not None:
            await run_allergy_check(basket, rx.customer_id, event.prescription_id, ctx)

    event_bus.subscribe(SaleCompleted, on_sale_completed)
    event_bus.subscribe(PrescriptionDispensed, on_prescription_dispensed)


def wire_medication_history(container: Container) -> None:
    """Fold a customer's dispensed drugs into their CRM medication history.

    Kept separate from :func:`wire_safety_checks` on purpose: that one only reads and
    warns, this one **writes** to crm, and mixing a write into the warn handler would
    blur its (read-only) intent and permission set. Both react to the same events but
    each reads its own source, which is an acceptable cost for a post-commit
    background reaction.

    Only fires when the transaction names a customer:

    * ``SaleCompleted`` → read the sale for its ``customer_id`` (the event contract is
      unchanged; the id is read back, not carried) and its sold items.
    * ``PrescriptionDispensed`` → read the prescription for its ``customer_id`` (always
      present) and its items.

    ``crm.record_medication_history`` self-limits: it records only with a current
    ``HEALTH`` consent, is idempotent per ``(source, ref_id)``, and never raises — so a
    walk-in with no customer, or a customer who didn't opt in, simply builds no history.
    """
    event_bus = container.resolve(EventBus)  # type: ignore[type-abstract]
    crm = container.resolve(CrmService)
    sales = container.resolve(SalesService)
    prescription = container.resolve(PrescriptionService)

    async def on_sale_completed(event: DomainEvent) -> None:
        assert isinstance(event, SaleCompleted)
        ctx = RequestContext(
            tenant_id=event.tenant_id,
            branch_id=event.branch_id,
            user_id=_SYSTEM_USER,
            permissions=_MEDHIST_PERMISSIONS,
        )
        try:
            sale = await sales.get_sale(event.order_id, ctx)
        except NotFoundError:
            return
        if sale.customer_id is None:
            return  # walk-in OTC sale, nobody to attribute the history to
        items = [
            MedicationHistoryItemInput(drug_id=it.drug_id, quantity=it.quantity)
            for it in event.items
        ]
        recorded = await crm.record_medication_history(
            sale.customer_id,
            items,
            MedicationHistorySource.SALE,
            event.order_id,
            event.occurred_at,
            ctx,
        )
        if recorded:
            _medhist_log.info(
                "medication_history_recorded",
                source="SALE",
                ref_id=str(event.order_id),
                entries=recorded,
            )

    async def on_prescription_dispensed(event: DomainEvent) -> None:
        assert isinstance(event, PrescriptionDispensed)
        ctx = RequestContext(
            tenant_id=event.tenant_id,
            branch_id=event.tenant_id,
            user_id=_SYSTEM_USER,
            permissions=_MEDHIST_PERMISSIONS,
        )
        try:
            rx = await prescription.get_prescription(event.prescription_id, ctx)
        except NotFoundError:
            return
        # Lịch sử dùng thuốc là hồ sơ CỦA MỘT NGƯỜI — không có khách thì không có hồ sơ
        # nào để ghi vào. Bỏ qua im lặng là đúng ở đây, không phải nuốt lỗi.
        if rx.customer_id is None:
            return
        items = [
            MedicationHistoryItemInput(drug_id=it.drug_id, quantity=it.quantity) for it in rx.items
        ]
        recorded = await crm.record_medication_history(
            rx.customer_id,
            items,
            MedicationHistorySource.PRESCRIPTION,
            event.prescription_id,
            event.occurred_at,
            ctx,
        )
        if recorded:
            _medhist_log.info(
                "medication_history_recorded",
                source="PRESCRIPTION",
                ref_id=str(event.prescription_id),
                entries=recorded,
            )

    event_bus.subscribe(SaleCompleted, on_sale_completed)
    event_bus.subscribe(PrescriptionDispensed, on_prescription_dispensed)


# Thứ tự nặng-nhẹ để chọn ra cảnh báo nặng nhất khi một giỏ có nhiều xung đột.
# Đặt ở composition root chứ không trong module nào: đây là việc **gộp để hiển thị**,
# không phải luật lâm sàng — `clinical` quyết CÓ xung đột hay không và nặng cỡ nào,
# chỗ này chỉ sắp chúng lại. Mức độ lạ (crm thêm sau) xếp 0: vẫn tính là xung đột,
# chỉ không được chọn làm "nặng nhất" nếu có mức đã biết.
_SEVERITY_RANK: dict[str, int] = {"SEVERE": 3, "MODERATE": 2, "MILD": 1}


class CrmClinicalAllergyRiskProvider:
    """Adapter cấp phán quyết dị ứng cho `sales`, để sales không import crm/clinical.

    Hiện thực cổng ``AllergyRiskProvider`` bằng cách nối lại **ba mảnh đã có sẵn**,
    không viết luật mới (kỷ luật #16):

    * ``catalog.get_drug_ingredients`` — giỏ hàng ra danh sách hoạt chất
    * ``crm.allergy_severities_for_safety_check`` — dị ứng khách đã khai; đây là
      đường đọc **có chủ đích** cho phép kiểm máy: không gác sau ``crm.sensitive.read``
      (duyệt Q3), trả **id + mức độ** chứ không trả hồ sơ/tên/bệnh nền, và ghi audit
      riêng ``CUSTOMER_SENSITIVE_AUTO_CHECK``
    * ``clinical.check_allergies`` — phép khớp thật (``find_allergy_alerts``)

    Vì sao vẫn phải gọi thêm ``crm.get_customer``: hàm safety-check trả ``{}`` cho **cả
    hai** trường hợp *"khách không có dị ứng nào"* và *"chưa đồng ý nên không được xem"*.
    Hai cái đó khác hẳn nhau ở quầy (xem :class:`AllergyRisk`), nên ``health_data_allowed``
    phải đọc riêng. Lượt đọc này chỉ cần ``crm.read`` và **không** kéo theo dữ liệu sức
    khoẻ — ``CustomerOutput`` giữ lại cờ đồng ý ngay cả khi giấu danh sách dị ứng.
    """

    def __init__(self, catalog: CatalogService, crm: CrmService, clinical: ClinicalService) -> None:
        self._catalog = catalog
        self._crm = crm
        self._clinical = clinical

    async def for_sale(
        self, drug_ids: frozenset[UUID], customer_id: UUID, tenant_id: UUID
    ) -> AllergyRisk | None:
        ctx = RequestContext(
            tenant_id=tenant_id,
            branch_id=tenant_id,
            user_id=_SYSTEM_USER,
            permissions=_SAFETY_PERMISSIONS,
        )
        try:
            customer = await self._crm.get_customer(customer_id, ctx)
        except NotFoundError:
            return None  # đơn ghi một khách không còn tồn tại — không có gì để đối chiếu
        if not customer.health_data_allowed:
            # Chưa đồng ý ⇒ phép kiểm KHÔNG CHẠY. Trả về nói rõ điều đó thay vì trả
            # một kết quả sạch — quầy phải phân biệt được hai thứ.
            return AllergyRisk(consent_granted=False)

        severities = await self._crm.allergy_severities_for_safety_check(customer_id, ctx)
        if not severities:
            return AllergyRisk(consent_granted=True)

        basket: list[BasketIngredient] = []
        seen: set[UUID] = set()
        for drug_id in drug_ids:
            try:
                refs = await self._catalog.get_drug_ingredients(drug_id, ctx)
            except NotFoundError:
                continue  # thuốc không có trong danh mục thì không đối chiếu được
            for ref in refs:
                if ref.ingredient_id not in seen:
                    seen.add(ref.ingredient_id)
                    basket.append(BasketIngredient(ingredient_id=ref.ingredient_id, name=ref.name))
        if not basket:
            return AllergyRisk(consent_granted=True)

        result = await self._clinical.check_allergies(
            CheckAllergiesInput(
                basket=basket, allergy_severities=severities, context_id=customer_id
            ),
            ctx,
        )
        if not result.alerts:
            return AllergyRisk(consent_granted=True)
        worst = max(result.alerts, key=lambda a: _SEVERITY_RANK.get(a.severity, 0))
        return AllergyRisk(
            consent_granted=True,
            conflict_count=len(result.alerts),
            worst_severity=worst.severity,
        )


class CatalogDrugInfoProvider:
    """Adapter making catalog the authority for a sale's Rx status.

    Implements the sales ``DrugInfoProvider`` port over ``CatalogService`` — the
    dependency lives here in ``api`` so sales never imports catalog.
    """

    def __init__(self, catalog: CatalogService) -> None:
        self._catalog = catalog

    async def get(self, drug_id: UUID, tenant_id: UUID) -> DrugInfo | None:
        ctx = RequestContext(
            tenant_id=tenant_id,
            branch_id=tenant_id,
            user_id=_SYSTEM_USER,
            permissions=frozenset({"catalog.read"}),
        )
        try:
            drug = await self._catalog.get_drug(drug_id, ctx)
        except NotFoundError:
            return None
        return DrugInfo(
            drug_id=drug_id,
            requires_prescription=drug.prescription_required,
            name=drug.name,
            unit=drug.base_unit,
            sale_price=drug.sale_price,
        )


class CatalogDrugMasterProvider:
    """Adapter for compliance's ``DrugMasterProvider`` (docs/13 mục B, C.7).

    First real wiring of this port — it was defined alongside ``NationalDrugRecord`` for QĐ540
    Bảng 1 but never implemented. Reused as-is 2026-07-25 for the Mẫu số 06 periodic report
    (NĐ163 Điều 35.2), which needs the same catalog facts (name/form/strength/registration_no/
    base_unit). Same shape as :class:`CatalogDrugInfoProvider` above — compliance never imports
    catalog directly.
    """

    def __init__(self, catalog: CatalogService) -> None:
        self._catalog = catalog

    async def get(self, drug_id: UUID, tenant_id: UUID) -> DrugMasterFacts | None:
        ctx = RequestContext(
            tenant_id=tenant_id,
            branch_id=tenant_id,
            user_id=_SYSTEM_USER,
            permissions=frozenset({"catalog.read"}),
        )
        try:
            drug = await self._catalog.get_drug(drug_id, ctx)
            ingredients = await self._catalog.get_drug_ingredients(drug_id, ctx)
        except NotFoundError:
            return None
        return DrugMasterFacts(
            registration_no=drug.registration_no,
            base_unit=drug.base_unit,
            name=drug.name,
            form=drug.form,
            strength=drug.strength,
            active_ingredients=" + ".join(ref.name for ref in ingredients),
        )


#: iam's step-up vocabulary → compliance's. Exhaustive by construction: mypy rejects a
#: missing key the moment either enum gains a member, which is what keeps the two from
#: drifting apart silently.
_STEP_UP_TO_SIGNING: dict[StepUpResult, SigningReauthOutcome] = {
    StepUpResult.OK: SigningReauthOutcome.OK,
    StepUpResult.BAD_PASSWORD: SigningReauthOutcome.BAD_PASSWORD,
    StepUpResult.CODE_REQUIRED: SigningReauthOutcome.CODE_REQUIRED,
    StepUpResult.BAD_CODE: SigningReauthOutcome.BAD_CODE,
    StepUpResult.ENROLLMENT_REQUIRED: SigningReauthOutcome.ENROLLMENT_REQUIRED,
}


class IamAuthReauthProvider:
    """Adapter for compliance's ``SigningReauthProvider`` (docs/13 mục C.5, ký sổ hướng A).

    Bọc ``iam.AuthService.verify_own_password`` — ``compliance`` cần xác minh mật khẩu của
    người dùng hiện tại trước khi ký, nhưng không sở hữu ``User``/mật khẩu (thuộc ``iam``).
    Cùng vị trí/hình dạng với :class:`CatalogDrugMasterProvider` — compliance không import
    iam trực tiếp. Không dùng ``_SYSTEM_USER`` giả — ``ctx`` truyền vào đây LÀ ctx thật của
    người đang ký, không phải một ctx hệ thống dựng sẵn như các adapter phản ứng sự kiện ở
    trên (xem docs/features/tt18-kiem-soat-dac-biet/02_DECISIONS_KY_SO.md Bước 3).
    """

    def __init__(self, auth: AuthService) -> None:
        self._auth = auth

    async def verify(
        self, ctx: RequestContext, plain_password: str, totp_code: str | None
    ) -> SigningReauthOutcome:
        """Re-auth both factors, translating iam's vocabulary into compliance's.

        The translation is the whole point of this adapter existing: ``compliance``
        defines its own :class:`SigningReauthOutcome` and never learns that ``iam``
        (or its :class:`StepUpResult`) exists, so module-independence holds while the
        two still agree on meaning. A new member on either side stops here as a mypy
        error rather than silently mapping to something wrong.
        """
        result = await self._auth.verify_step_up(ctx, plain_password, totp_code)
        return _STEP_UP_TO_SIGNING[result]


class PrescriptionInfoAdapter:
    """Adapter making prescription the authority for a sale's ``prescription_ref``.

    Implements the sales ``PrescriptionInfoProvider`` port over ``PrescriptionService``
    — the dependency lives here in ``api`` so sales never imports prescription. Lets
    ``complete_sale`` verify an ETC order's ref is a real, sale-authorising Rx (S5.4).
    """

    def __init__(self, prescription: PrescriptionService) -> None:
        self._prescription = prescription

    async def get(self, prescription_id: UUID, tenant_id: UUID) -> PrescriptionInfo | None:
        ctx = RequestContext(
            tenant_id=tenant_id,
            branch_id=tenant_id,
            user_id=_SYSTEM_USER,
            permissions=frozenset({"rx.read"}),
        )
        try:
            rx = await self._prescription.get_prescription(prescription_id, ctx)
        except NotFoundError:
            return None
        return PrescriptionInfo(prescription_id=prescription_id, status=rx.status)


class SalesLoyaltyAccrualReader:
    """Nối `crm` → `sales` để màn Khách hàng hiện điểm đã tích trong năm.

    Adapter, không phải logic: phép cộng nằm ở `sales` (nơi có đơn hàng), mốc năm nằm ở
    `crm.loyalty` (nơi có luật tích điểm). Chỗ này chỉ ráp hai thứ lại — kỷ luật #16.

    Chạy dưới **danh tính hệ thống**: nhân viên xem danh sách khách chỉ cần `crm.read`,
    không phải cấp thêm `sales.read` trên toàn bộ đơn hàng chỉ để thấy một con số tổng.
    Cùng khuôn với adapter tên thuốc cho `analytics` (§7bt).
    """

    def __init__(self, sales: SalesService) -> None:
        self._sales = sales

    async def accrued_this_year(
        self, customer_ids: Sequence[UUID], tenant_id: UUID
    ) -> dict[UUID, Decimal]:
        # Năm DƯƠNG LỊCH, đúng như Chain chốt 29/07 cho chương trình khách quen. Mốc tính
        # theo giờ UTC vì `created_at` lưu UTC; lệch múi giờ chỉ ảnh hưởng đơn trong vài
        # giờ quanh giao thừa, và đổi mốc sang giờ VN là một quyết định nghiệp vụ riêng.
        dau_nam = datetime(datetime.now(UTC).year, 1, 1, tzinfo=UTC)
        het_nam = datetime(dau_nam.year + 1, 1, 1, tzinfo=UTC)
        ctx = RequestContext(
            tenant_id=tenant_id,
            # Tổng theo tenant, không theo chi nhánh: khách tích điểm với NHÀ THUỐC, mua ở
            # cơ sở nào cũng vậy. `branch_id` phải có giá trị nên dùng chính tenant.
            branch_id=tenant_id,
            user_id=_SYSTEM_USER,
            permissions=_SYSTEM_PERMISSIONS,
        )
        return await self._sales.accrued_by_customer(
            customer_ids, ctx, created_from=dau_nam, created_to=het_nam
        )
