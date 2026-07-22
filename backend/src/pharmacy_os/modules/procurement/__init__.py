"""Procurement module: suppliers, purchase orders, and goods receipt notes.

Lifecycle: ``PurchaseOrder`` DRAFT → ORDERED → (PARTIALLY_RECEIVED | RECEIVED)
→ CLOSED, or DRAFT → CANCELLED. A ``GoodsReceiptNote`` records what actually
arrived against a PO and, once confirmed, updates that PO's received
quantities. Turning a confirmed GRN into ``inventory`` batches/stock movements
is cross-module and handled at the composition root in a later step — this
module only models the procurement-side lifecycle.
"""
