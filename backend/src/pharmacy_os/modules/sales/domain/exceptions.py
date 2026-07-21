"""Sales domain exceptions (pure — no framework)."""

from __future__ import annotations


class SalesError(Exception):
    """Base for sales domain rule violations."""


class EmptyOrderError(SalesError):
    """Raised when completing an order that has no lines."""


class PrescriptionRequiredError(SalesError):
    """Raised when selling a prescription drug (ETC/CONTROLLED) without a valid Rx."""


class InvalidOrderStateError(SalesError):
    """Raised on an operation not allowed in the order's current status."""


class UnderpaidError(SalesError):
    """Raised when recorded payments do not cover the order subtotal."""


class InvalidReturnError(SalesError):
    """Raised when a return references an unknown line or an impossible quantity."""
