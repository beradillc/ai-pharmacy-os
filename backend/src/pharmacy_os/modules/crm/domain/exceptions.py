"""CRM domain exceptions (pure — no framework)."""

from __future__ import annotations


class CrmError(Exception):
    """Base for crm domain rule violations."""


class InvalidCustomerError(CrmError):
    """Raised when a :class:`Customer` is malformed."""


class DuplicateAllergyError(CrmError):
    """Raised when adding an allergy for an ingredient already recorded."""


class InvalidConditionError(CrmError):
    """Raised when a :class:`Condition` is malformed."""


class DuplicateConditionError(CrmError):
    """Raised when adding a condition code already recorded."""


class InvalidMedicationHistoryEntryError(CrmError):
    """Raised when a :class:`MedicationHistoryEntry` is malformed."""
