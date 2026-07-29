"""Procurement domain exceptions (pure — no framework)."""

from __future__ import annotations


class ProcurementError(Exception):
    """Base for procurement domain rule violations."""


class InvalidSupplierError(ProcurementError):
    """Raised when a :class:`Supplier` is malformed."""


class InvalidPurchaseOrderItemError(ProcurementError):
    """Raised when a :class:`PurchaseOrderItem` is malformed."""


class EmptyPurchaseOrderError(ProcurementError):
    """Raised when placing an order that has no items."""


class InvalidPurchaseOrderStateError(ProcurementError):
    """Raised on a :class:`PurchaseOrder` operation not allowed in its current status."""


class UnknownPurchaseOrderItemError(ProcurementError):
    """Raised when a received line references a PO item that doesn't exist on the order."""


class DrugMismatchError(ProcurementError):
    """Raised when a received line names a different drug than the PO line ordered.

    Not a typo guard — a traceability guard. Crediting stock to the wrong drug
    leaves the PO reading "received" while nothing sellable arrived under that
    drug, so nobody goes looking. See ``ProcurementService.create_goods_receipt``
    for the measurement that found this (2026-07-29).
    """


class OverReceiptError(ProcurementError):
    """Raised when applying a receipt would exceed a line's ordered quantity."""


class InvalidGoodsReceiptItemError(ProcurementError):
    """Raised when a :class:`GoodsReceiptItem` is malformed."""


class EmptyGoodsReceiptError(ProcurementError):
    """Raised when confirming a goods receipt note that has no items."""


class InvalidGoodsReceiptStateError(ProcurementError):
    """Raised on a :class:`GoodsReceiptNote` operation not allowed in its current status."""
