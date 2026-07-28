from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from pharmacy_os.modules.procurement.domain import (
    EmptyGoodsReceiptError,
    EmptyPurchaseOrderError,
    GoodsReceiptItem,
    GoodsReceiptNote,
    GoodsReceiptStatus,
    InvalidGoodsReceiptItemError,
    InvalidGoodsReceiptStateError,
    InvalidPurchaseOrderItemError,
    InvalidPurchaseOrderStateError,
    InvalidSupplierError,
    OverReceiptError,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    Supplier,
    UnknownPurchaseOrderItemError,
)


def _supplier(**kw: object) -> Supplier:
    return Supplier(tenant_id=uuid4(), name="Nhà cung cấp Dược Việt", **kw)  # type: ignore[arg-type]


def _po_item(*, qty: str = "100", price: str = "5000") -> PurchaseOrderItem:
    return PurchaseOrderItem(
        drug_id=uuid4(), quantity_ordered=Decimal(qty), unit_price=Decimal(price)
    )


def _po(**kw: object) -> PurchaseOrder:
    return PurchaseOrder(
        tenant_id=uuid4(),
        branch_id=uuid4(),
        supplier_id=uuid4(),
        code="PO-0001",
        **kw,  # type: ignore[arg-type]
    )


def _grn_item(po_item: PurchaseOrderItem, *, qty: str) -> GoodsReceiptItem:
    return GoodsReceiptItem(
        po_item_id=po_item.id,
        drug_id=po_item.drug_id,
        quantity_received=Decimal(qty),
        lot_no="LOT001",
        expiry_date=date.today() + timedelta(days=365),
        unit_cost=Decimal("4800"),
    )


def _grn(po: PurchaseOrder, **kw: object) -> GoodsReceiptNote:
    return GoodsReceiptNote(
        tenant_id=po.tenant_id,
        branch_id=po.branch_id,
        po_id=po.id,
        received_by=uuid4(),
        **kw,  # type: ignore[arg-type]
    )


# --- Supplier ---


def test_supplier_requires_non_empty_name() -> None:
    with pytest.raises(InvalidSupplierError):
        Supplier(tenant_id=uuid4(), name="  ")


def test_supplier_deactivate() -> None:
    supplier = _supplier()
    assert supplier.is_active is True
    supplier.deactivate()
    assert supplier.is_active is False


# --- PurchaseOrderItem ---


def test_purchase_order_item_rejects_non_positive_quantity() -> None:
    with pytest.raises(InvalidPurchaseOrderItemError):
        PurchaseOrderItem(drug_id=uuid4(), quantity_ordered=Decimal("0"), unit_price=Decimal("100"))


def test_purchase_order_item_rejects_negative_price() -> None:
    with pytest.raises(InvalidPurchaseOrderItemError):
        PurchaseOrderItem(drug_id=uuid4(), quantity_ordered=Decimal("10"), unit_price=Decimal("-1"))


# --- PurchaseOrder lifecycle ---


def test_new_purchase_order_is_draft() -> None:
    po = _po()
    assert po.status is PurchaseOrderStatus.DRAFT
    assert po.ordered_at is None


def test_add_item_while_draft() -> None:
    po = _po()
    po.add_item(_po_item())
    assert len(po.items) == 1


def test_place_order_happy_path() -> None:
    po = _po()
    po.add_item(_po_item())
    po.place_order()
    assert po.status is PurchaseOrderStatus.ORDERED
    assert po.ordered_at is not None


def test_place_order_empty_rejected() -> None:
    po = _po()
    with pytest.raises(EmptyPurchaseOrderError):
        po.place_order()


def test_place_order_twice_rejected() -> None:
    po = _po()
    po.add_item(_po_item())
    po.place_order()
    with pytest.raises(InvalidPurchaseOrderStateError):
        po.place_order()


def test_add_item_after_ordered_rejected() -> None:
    po = _po()
    po.add_item(_po_item())
    po.place_order()
    with pytest.raises(InvalidPurchaseOrderStateError):
        po.add_item(_po_item())


def test_cancel_from_draft() -> None:
    po = _po()
    po.cancel()
    assert po.status is PurchaseOrderStatus.CANCELLED


def test_cancel_after_ordered_rejected() -> None:
    po = _po()
    po.add_item(_po_item())
    po.place_order()
    with pytest.raises(InvalidPurchaseOrderStateError):
        po.cancel()


# --- PurchaseOrder.apply_receipt / GoodsReceiptNote ---


def test_apply_receipt_partial_sets_partially_received() -> None:
    po = _po()
    item = _po_item(qty="100")
    po.add_item(item)
    po.place_order()
    po.apply_receipt([_grn_item(item, qty="40")])
    assert po.status is PurchaseOrderStatus.PARTIALLY_RECEIVED
    assert item.quantity_received == Decimal("40")


def test_apply_receipt_full_sets_received() -> None:
    po = _po()
    item = _po_item(qty="100")
    po.add_item(item)
    po.place_order()
    po.apply_receipt([_grn_item(item, qty="100")])
    assert po.status is PurchaseOrderStatus.RECEIVED


def test_apply_receipt_accumulates_across_multiple_grns() -> None:
    po = _po()
    item = _po_item(qty="100")
    po.add_item(item)
    po.place_order()
    po.apply_receipt([_grn_item(item, qty="40")])
    assert po.status is PurchaseOrderStatus.PARTIALLY_RECEIVED
    po.apply_receipt([_grn_item(item, qty="60")])
    assert po.status is PurchaseOrderStatus.RECEIVED
    assert item.quantity_received == Decimal("100")


def test_apply_receipt_before_ordered_rejected() -> None:
    po = _po()
    item = _po_item()
    po.add_item(item)
    with pytest.raises(InvalidPurchaseOrderStateError):
        po.apply_receipt([_grn_item(item, qty="10")])


def test_apply_receipt_over_ordered_quantity_rejected() -> None:
    po = _po()
    item = _po_item(qty="100")
    po.add_item(item)
    po.place_order()
    with pytest.raises(OverReceiptError):
        po.apply_receipt([_grn_item(item, qty="150")])


def test_apply_receipt_unknown_po_item_rejected() -> None:
    po = _po()
    item = _po_item(qty="100")
    po.add_item(item)
    po.place_order()
    foreign_item = _po_item(qty="10")
    with pytest.raises(UnknownPurchaseOrderItemError):
        po.apply_receipt([_grn_item(foreign_item, qty="5")])


def test_close_requires_received() -> None:
    po = _po()
    item = _po_item(qty="100")
    po.add_item(item)
    po.place_order()
    with pytest.raises(InvalidPurchaseOrderStateError):
        po.close()


def test_close_happy_path() -> None:
    po = _po()
    item = _po_item(qty="100")
    po.add_item(item)
    po.place_order()
    po.apply_receipt([_grn_item(item, qty="100")])
    po.close()
    assert po.status is PurchaseOrderStatus.CLOSED


# --- GoodsReceiptItem ---


def test_goods_receipt_item_rejects_non_positive_quantity() -> None:
    with pytest.raises(InvalidGoodsReceiptItemError):
        GoodsReceiptItem(
            po_item_id=uuid4(),
            drug_id=uuid4(),
            quantity_received=Decimal("0"),
            lot_no="LOT001",
            expiry_date=date.today() + timedelta(days=30),
            unit_cost=Decimal("100"),
        )


def test_goods_receipt_item_rejects_empty_lot_no() -> None:
    with pytest.raises(InvalidGoodsReceiptItemError):
        GoodsReceiptItem(
            po_item_id=uuid4(),
            drug_id=uuid4(),
            quantity_received=Decimal("10"),
            lot_no="  ",
            expiry_date=date.today() + timedelta(days=30),
            unit_cost=Decimal("100"),
        )


def test_goods_receipt_item_rejects_negative_cost() -> None:
    with pytest.raises(InvalidGoodsReceiptItemError):
        GoodsReceiptItem(
            po_item_id=uuid4(),
            drug_id=uuid4(),
            quantity_received=Decimal("10"),
            lot_no="LOT001",
            expiry_date=date.today() + timedelta(days=30),
            unit_cost=Decimal("-1"),
        )


# --- GoodsReceiptNote lifecycle ---


def test_new_goods_receipt_is_draft() -> None:
    po = _po()
    grn = _grn(po)
    assert grn.status is GoodsReceiptStatus.DRAFT


def test_confirm_empty_receipt_rejected() -> None:
    po = _po()
    grn = _grn(po)
    with pytest.raises(EmptyGoodsReceiptError):
        grn.confirm()


def test_confirm_happy_path() -> None:
    po = _po()
    item = _po_item()
    po.add_item(item)
    grn = _grn(po)
    grn.add_item(_grn_item(item, qty="40"))
    grn.confirm()
    assert grn.status is GoodsReceiptStatus.CONFIRMED


def test_confirm_twice_rejected() -> None:
    po = _po()
    item = _po_item()
    po.add_item(item)
    grn = _grn(po)
    grn.add_item(_grn_item(item, qty="40"))
    grn.confirm()
    with pytest.raises(InvalidGoodsReceiptStateError):
        grn.confirm()


def test_add_item_after_confirmed_rejected() -> None:
    po = _po()
    item = _po_item()
    po.add_item(item)
    grn = _grn(po)
    grn.add_item(_grn_item(item, qty="40"))
    grn.confirm()
    with pytest.raises(InvalidGoodsReceiptStateError):
        grn.add_item(_grn_item(item, qty="10"))
