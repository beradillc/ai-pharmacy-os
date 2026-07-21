"""Compliance domain exceptions (pure — no framework)."""

from __future__ import annotations


class ComplianceError(Exception):
    """Base for compliance domain rule violations."""


class NotControlledSubstanceError(ComplianceError):
    """Raised when creating a ``ControlledLedgerEntry`` for a non-controlled category."""


class MissingControlledCustomerDetailError(ComplianceError):
    """GN/HT/TC sale lacks required customer detail (Phụ lục XXI, TT 20/2017)."""


class MissingControlledPrescriptionCodeError(ComplianceError):
    """GN/HT sale lacks the retained ``prescription_code`` (Điều 15.1.c, TT 20/2017)."""


class MissingEtcPrescriptionFieldsError(ComplianceError):
    """Feature-flagged ETC prescription rule (docs/13 mục C.3.1) is enabled and unmet."""


class InvalidSyncStateError(ComplianceError):
    """Raised on a ``NationalSyncLog`` transition not allowed in its current status."""
