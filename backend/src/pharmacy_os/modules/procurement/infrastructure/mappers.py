"""Mapping between procurement ORM rows and domain entities."""

from __future__ import annotations

from pharmacy_os.modules.procurement.domain import (
    GoodsReceiptItem,
    GoodsReceiptNote,
    GoodsReceiptStatus,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    Supplier,
)
from pharmacy_os.modules.procurement.infrastructure.models import (
    GoodsReceiptItemORM,
    GoodsReceiptORM,
    PurchaseOrderItemORM,
    PurchaseOrderORM,
    SupplierORM,
)


def supplier_to_domain(row: SupplierORM) -> Supplier:
    return Supplier(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        tax_code=row.tax_code,
        contact_name=row.contact_name,
        phone=row.phone,
        email=row.email,
        address=row.address,
        is_active=row.is_active,
    )


def supplier_to_orm(supplier: Supplier) -> SupplierORM:
    return SupplierORM(
        id=supplier.id,
        tenant_id=supplier.tenant_id,
        name=supplier.name,
        tax_code=supplier.tax_code,
        contact_name=supplier.contact_name,
        phone=supplier.phone,
        email=supplier.email,
        address=supplier.address,
        is_active=supplier.is_active,
    )


def purchase_order_to_domain(row: PurchaseOrderORM) -> PurchaseOrder:
    po = PurchaseOrder(
        id=row.id,
        tenant_id=row.tenant_id,
        branch_id=row.branch_id,
        supplier_id=row.supplier_id,
        status=PurchaseOrderStatus(row.status),
        created_at=row.created_at,
        ordered_at=row.ordered_at,
    )
    po.items = [
        PurchaseOrderItem(
            id=it.id,
            drug_id=it.drug_id,
            quantity_ordered=it.quantity_ordered,
            unit_price=it.unit_price,
            quantity_received=it.quantity_received,
        )
        for it in row.items
    ]
    return po


def purchase_order_to_orm(po: PurchaseOrder) -> PurchaseOrderORM:
    return PurchaseOrderORM(
        id=po.id,
        tenant_id=po.tenant_id,
        branch_id=po.branch_id,
        supplier_id=po.supplier_id,
        status=po.status.value,
        created_at=po.created_at,
        ordered_at=po.ordered_at,
        items=[
            PurchaseOrderItemORM(
                id=it.id,
                purchase_order_id=po.id,
                drug_id=it.drug_id,
                quantity_ordered=it.quantity_ordered,
                unit_price=it.unit_price,
                quantity_received=it.quantity_received,
            )
            for it in po.items
        ],
    )


def goods_receipt_to_domain(row: GoodsReceiptORM) -> GoodsReceiptNote:
    grn = GoodsReceiptNote(
        id=row.id,
        tenant_id=row.tenant_id,
        branch_id=row.branch_id,
        po_id=row.po_id,
        received_by=row.received_by,
        status=GoodsReceiptStatus(row.status),
        received_at=row.received_at,
    )
    grn.items = [
        GoodsReceiptItem(
            id=it.id,
            po_item_id=it.po_item_id,
            drug_id=it.drug_id,
            quantity_received=it.quantity_received,
            lot_no=it.lot_no,
            expiry_date=it.expiry_date,
            unit_cost=it.unit_cost,
            mfg_date=it.mfg_date,
        )
        for it in row.items
    ]
    return grn


def goods_receipt_to_orm(grn: GoodsReceiptNote) -> GoodsReceiptORM:
    return GoodsReceiptORM(
        id=grn.id,
        tenant_id=grn.tenant_id,
        branch_id=grn.branch_id,
        po_id=grn.po_id,
        received_by=grn.received_by,
        status=grn.status.value,
        received_at=grn.received_at,
        items=[
            GoodsReceiptItemORM(
                id=it.id,
                goods_receipt_id=grn.id,
                po_item_id=it.po_item_id,
                drug_id=it.drug_id,
                quantity_received=it.quantity_received,
                lot_no=it.lot_no,
                expiry_date=it.expiry_date,
                unit_cost=it.unit_cost,
                mfg_date=it.mfg_date,
            )
            for it in grn.items
        ],
    )
