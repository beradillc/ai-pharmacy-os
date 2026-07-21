"""Prescription module: intake, pharmacist validation/rejection and dispense.

Lifecycle: DRAFT → VALIDATED → DISPENSED, or DRAFT/VALIDATED → REJECTED. This
module models the Rx lifecycle only — linking a dispensed prescription to a
sale (``SalesOrder.prescription_ref``) and clinical safety checks are handled
by other modules (sales already supports the reference; clinical arrives in a
later Sprint 5 step).
"""
