"""Sales domain exceptions (pure — no framework)."""

from __future__ import annotations


class SalesError(Exception):
    """Base for sales domain rule violations."""


class EmptyOrderError(SalesError):
    """Raised when completing an order that has no lines."""


class PrescriptionRequiredError(SalesError):
    """Raised when selling a prescription drug (ETC/CONTROLLED) without a valid Rx."""


class InvalidPrescriptionRefError(SalesError):
    """Raised when a sale's ``prescription_ref`` is not a real, sale-authorising Rx.

    Distinct from :class:`PrescriptionRequiredError` (which means *no* ref at all):
    here a ref was supplied but the referenced prescription does not exist for the
    tenant, or is not in a state that authorises selling its ETC items.
    """


class InvalidOrderStateError(SalesError):
    """Raised on an operation not allowed in the order's current status."""


class UnderpaidError(SalesError):
    """Raised when recorded payments do not cover the order subtotal."""


class InvalidReturnError(SalesError):
    """Raised when a return references an unknown line or an impossible quantity."""


class AllergyAcknowledgementRequiredError(SalesError):
    """Raised when completing a sale that collides with a declared allergy without
    the seller recording a reason for dispensing anyway.

    Not a prohibition — quyết định Đ-6 chose *warn plus acknowledgement* over a hard
    block, so supplying a reason clears this. See
    :func:`~pharmacy_os.modules.sales.domain.rules.ensure_allergy_acknowledged` for
    why the gate sits at completion time rather than where the warning is shown.
    """
