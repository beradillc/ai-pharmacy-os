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


class InvalidConsentError(CrmError):
    """Raised when a :class:`CustomerConsent` record is malformed."""


class ConsentRequiredError(CrmError):
    """Raised when health data is touched without an active ``HEALTH`` consent.

    Consent is the **only** legal basis for holding a customer's health data (Luật
    91/2025 Điều 26.1 — no statute obliges a pharmacy to keep allergy records), so
    this is not a policy toggle: without it there is no lawful basis to process, and
    the domain refuses rather than leaving the check to a caller who might forget.
    """


class CustomerAnonymisedError(CrmError):
    """Raised when writing to a record whose identity has already been stripped.

    Anonymisation is one-way by design (duyệt Q2): re-attaching a name would defeat
    the erasure request it was performed for.
    """
