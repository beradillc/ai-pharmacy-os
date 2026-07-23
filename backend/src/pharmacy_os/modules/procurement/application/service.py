"""Procurement use-cases: suppliers, purchase orders, goods receipt notes.

The service depends only on ports; the concrete repositories and unit of work are
injected as factories at composition time (see the module ``register``).
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from pharmacy_os.core.audit import AuditAction, AuditEntry, AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import NotFoundError, ValidationError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.procurement.application.dto import (
    CreateGoodsReceiptInput,
    CreatePurchaseOrderInput,
    CreateSupplierInput,
    GoodsReceiptOutput,
    PurchaseOrderItemInput,
    PurchaseOrderOutput,
    SupplierOutput,
)
from pharmacy_os.modules.procurement.domain import (
    GoodsReceiptItem,
    GoodsReceiptNote,
    GoodsReceived,
    ProcurementError,
    PurchaseOrder,
    PurchaseOrdered,
    PurchaseOrderItem,
    ReceivedItem,
    Supplier,
    UnknownPurchaseOrderItemError,
)
from pharmacy_os.modules.procurement.domain.ports import (
    GoodsReceiptRepository,
    PurchaseOrderRepository,
    SupplierRepository,
)

UowFactory = Callable[[], UnitOfWork]
SupplierRepoFactory = Callable[[UnitOfWork, RequestContext], SupplierRepository]
PurchaseOrderRepoFactory = Callable[[UnitOfWork, RequestContext], PurchaseOrderRepository]
GoodsReceiptRepoFactory = Callable[[UnitOfWork, RequestContext], GoodsReceiptRepository]


class ProcurementService:
    def __init__(
        self,
        uow_factory: UowFactory,
        supplier_repo_factory: SupplierRepoFactory,
        po_repo_factory: PurchaseOrderRepoFactory,
        grn_repo_factory: GoodsReceiptRepoFactory,
        audit: AuditLogger,
    ) -> None:
        self._uow_factory = uow_factory
        self._supplier_repo_factory = supplier_repo_factory
        self._po_repo_factory = po_repo_factory
        self._grn_repo_factory = grn_repo_factory
        self._audit = audit

    # --- Supplier ---

    async def create_supplier(
        self, data: CreateSupplierInput, ctx: RequestContext
    ) -> SupplierOutput:
        require_permission(ctx, "procurement.supplier.create")
        try:
            supplier = Supplier(
                tenant_id=ctx.tenant_id,
                name=data.name,
                tax_code=data.tax_code,
                contact_name=data.contact_name,
                phone=data.phone,
                email=data.email,
                address=data.address,
            )
        except ProcurementError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._supplier_repo_factory(uow, ctx)
            await repo.add(supplier)
            await uow.commit()
        return SupplierOutput.of(supplier)

    async def get_supplier(self, supplier_id: UUID, ctx: RequestContext) -> SupplierOutput:
        require_permission(ctx, "procurement.supplier.read")
        supplier = await self._get_supplier_or_404(supplier_id, ctx)
        return SupplierOutput.of(supplier)

    async def list_suppliers(
        self, ctx: RequestContext, *, limit: int = 50, offset: int = 0
    ) -> list[SupplierOutput]:
        require_permission(ctx, "procurement.supplier.read")
        async with self._uow_factory() as uow:
            repo = self._supplier_repo_factory(uow, ctx)
            suppliers = await repo.list(limit=limit, offset=offset)
        return [SupplierOutput.of(s) for s in suppliers]

    # --- PurchaseOrder ---

    async def create_purchase_order(
        self, data: CreatePurchaseOrderInput, ctx: RequestContext
    ) -> PurchaseOrderOutput:
        """Create a DRAFT purchase order, optionally with its initial lines."""
        require_permission(ctx, "procurement.po.create")
        po = PurchaseOrder(
            tenant_id=ctx.tenant_id, branch_id=ctx.branch_id, supplier_id=data.supplier_id
        )
        try:
            for item in data.items:
                po.add_item(
                    PurchaseOrderItem(
                        drug_id=item.drug_id,
                        quantity_ordered=item.quantity_ordered,
                        unit_price=item.unit_price,
                    )
                )
        except ProcurementError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._po_repo_factory(uow, ctx)
            await repo.add(po)
            await uow.commit()
        return PurchaseOrderOutput.of(po)

    async def add_po_item(
        self, po_id: UUID, data: PurchaseOrderItemInput, ctx: RequestContext
    ) -> PurchaseOrderOutput:
        """Add a line to a still-DRAFT purchase order."""
        require_permission(ctx, "procurement.po.write")
        po = await self._get_po_or_404(po_id, ctx)
        try:
            po.add_item(
                PurchaseOrderItem(
                    drug_id=data.drug_id,
                    quantity_ordered=data.quantity_ordered,
                    unit_price=data.unit_price,
                )
            )
        except ProcurementError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._po_repo_factory(uow, ctx)
            await repo.update(po)
            await uow.commit()
        return PurchaseOrderOutput.of(po)

    async def mark_ordered(self, po_id: UUID, ctx: RequestContext) -> PurchaseOrderOutput:
        """Gửi NCC: DRAFT -> ORDERED. Emits ``PurchaseOrdered``."""
        require_permission(ctx, "procurement.po.write")
        po = await self._get_po_or_404(po_id, ctx)
        try:
            po.place_order()
        except ProcurementError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._po_repo_factory(uow, ctx)
            await repo.update(po)
            uow.collect(
                PurchaseOrdered(
                    tenant_id=ctx.tenant_id,
                    po_id=po.id,
                    branch_id=po.branch_id,
                    supplier_id=po.supplier_id,
                )
            )
            await uow.commit()
        await self._record(ctx, AuditAction.PROCUREMENT_PO_ORDERED, "purchase_order", po.id)
        return PurchaseOrderOutput.of(po)

    async def cancel_purchase_order(self, po_id: UUID, ctx: RequestContext) -> PurchaseOrderOutput:
        """Only allowed while still DRAFT."""
        require_permission(ctx, "procurement.po.write")
        po = await self._get_po_or_404(po_id, ctx)
        try:
            po.cancel()
        except ProcurementError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._po_repo_factory(uow, ctx)
            await repo.update(po)
            await uow.commit()
        return PurchaseOrderOutput.of(po)

    async def close_purchase_order(self, po_id: UUID, ctx: RequestContext) -> PurchaseOrderOutput:
        """Đối chiếu xong: RECEIVED -> CLOSED."""
        require_permission(ctx, "procurement.po.write")
        po = await self._get_po_or_404(po_id, ctx)
        try:
            po.close()
        except ProcurementError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._po_repo_factory(uow, ctx)
            await repo.update(po)
            await uow.commit()
        return PurchaseOrderOutput.of(po)

    async def get_purchase_order(self, po_id: UUID, ctx: RequestContext) -> PurchaseOrderOutput:
        require_permission(ctx, "procurement.po.read")
        po = await self._get_po_or_404(po_id, ctx)
        return PurchaseOrderOutput.of(po)

    # --- GoodsReceiptNote ---

    async def create_goods_receipt(
        self, data: CreateGoodsReceiptInput, ctx: RequestContext
    ) -> GoodsReceiptOutput:
        """Create a DRAFT goods receipt note against an existing purchase order.

        Each line's ``po_item_id`` is checked against the PO's own items here
        (both in the same module, already loaded) rather than left to surface as
        a raw FK ``IntegrityError`` on insert or be caught late at
        :meth:`confirm_goods_receipt` — same failure mode ``apply_receipt``
        guards against, just reported earlier.
        """
        require_permission(ctx, "procurement.grn.create")
        po = await self._get_po_or_404(data.po_id, ctx)
        known_item_ids = {item.id for item in po.items}
        grn = GoodsReceiptNote(
            tenant_id=po.tenant_id,
            branch_id=po.branch_id,
            po_id=po.id,
            received_by=ctx.user_id,
        )
        try:
            for item in data.items:
                if item.po_item_id not in known_item_ids:
                    raise UnknownPurchaseOrderItemError(
                        f"Dòng hàng {item.po_item_id} không thuộc đơn mua hàng {po.id}"
                    )
                grn.add_item(
                    GoodsReceiptItem(
                        po_item_id=item.po_item_id,
                        drug_id=item.drug_id,
                        quantity_received=item.quantity_received,
                        lot_no=item.lot_no,
                        expiry_date=item.expiry_date,
                        unit_cost=item.unit_cost,
                        mfg_date=item.mfg_date,
                    )
                )
        except ProcurementError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._grn_repo_factory(uow, ctx)
            await repo.add(grn)
            await uow.commit()
        return GoodsReceiptOutput.of(grn)

    async def confirm_goods_receipt(self, grn_id: UUID, ctx: RequestContext) -> GoodsReceiptOutput:
        """Confirm a GRN and fold its lines into the linked PO's received quantities.

        Emits ``GoodsReceived`` after commit — the composition-root step that turns
        this into ``inventory`` batches/stock movements is a later, separate step
        (not done here; see module docstring).
        """
        require_permission(ctx, "procurement.grn.confirm")
        grn = await self._get_grn_or_404(grn_id, ctx)
        po = await self._get_po_or_404(grn.po_id, ctx)
        try:
            grn.confirm()
            po.apply_receipt(grn.items)
        except ProcurementError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            grn_repo = self._grn_repo_factory(uow, ctx)
            po_repo = self._po_repo_factory(uow, ctx)
            await grn_repo.update(grn)
            await po_repo.update(po)
            uow.collect(
                GoodsReceived(
                    tenant_id=ctx.tenant_id,
                    grn_id=grn.id,
                    po_id=po.id,
                    branch_id=grn.branch_id,
                    received_by=grn.received_by,
                    items=tuple(
                        ReceivedItem(
                            drug_id=it.drug_id,
                            lot_no=it.lot_no,
                            expiry_date=it.expiry_date,
                            unit_cost=it.unit_cost,
                            quantity=it.quantity_received,
                            po_item_id=it.po_item_id,
                            mfg_date=it.mfg_date,
                        )
                        for it in grn.items
                    ),
                )
            )
            await uow.commit()
        await self._record(ctx, AuditAction.PROCUREMENT_GRN_CONFIRMED, "goods_receipt_note", grn.id)
        return GoodsReceiptOutput.of(grn)

    async def get_goods_receipt(self, grn_id: UUID, ctx: RequestContext) -> GoodsReceiptOutput:
        require_permission(ctx, "procurement.grn.read")
        grn = await self._get_grn_or_404(grn_id, ctx)
        return GoodsReceiptOutput.of(grn)

    # --- helpers ---

    async def _get_supplier_or_404(self, supplier_id: UUID, ctx: RequestContext) -> Supplier:
        async with self._uow_factory() as uow:
            repo = self._supplier_repo_factory(uow, ctx)
            supplier = await repo.get(supplier_id)
        if supplier is None:
            raise NotFoundError(f"Không tìm thấy nhà cung cấp {supplier_id}")
        return supplier

    async def _get_po_or_404(self, po_id: UUID, ctx: RequestContext) -> PurchaseOrder:
        async with self._uow_factory() as uow:
            repo = self._po_repo_factory(uow, ctx)
            po = await repo.get(po_id)
        if po is None:
            raise NotFoundError(f"Không tìm thấy đơn mua hàng {po_id}")
        return po

    async def _get_grn_or_404(self, grn_id: UUID, ctx: RequestContext) -> GoodsReceiptNote:
        async with self._uow_factory() as uow:
            repo = self._grn_repo_factory(uow, ctx)
            grn = await repo.get(grn_id)
        if grn is None:
            raise NotFoundError(f"Không tìm thấy phiếu nhập kho {grn_id}")
        return grn

    async def _record(
        self, ctx: RequestContext, action: AuditAction, target_type: str, target_id: UUID
    ) -> None:
        """Append one audit row — metadata only, never price/supplier contact content."""
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=action,
                target_type=target_type,
                target_id=str(target_id),
            ).with_context(client_ip=ctx.client_ip, branch_id=str(ctx.branch_id))
        )
