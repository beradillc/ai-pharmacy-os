"""Prescription domain exceptions (pure — no framework)."""

from __future__ import annotations


class PrescriptionError(Exception):
    """Base for prescription domain rule violations."""


class EmptyPrescriptionError(PrescriptionError):
    """Raised when validating a prescription that has no items."""


class InvalidPrescriptionStateError(PrescriptionError):
    """Raised on an operation not allowed in the prescription's current status."""
