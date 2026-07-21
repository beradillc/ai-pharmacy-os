"""Prescription domain events."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pharmacy_os.core.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PrescriptionValidated(DomainEvent):
    """Emitted when a pharmacist approves a prescription (DRAFT → VALIDATED)."""

    prescription_id: UUID
    validated_by: UUID


@dataclass(frozen=True, kw_only=True)
class PrescriptionRejected(DomainEvent):
    """Emitted when a prescription is rejected, from DRAFT or VALIDATED."""

    prescription_id: UUID
    reason: str


@dataclass(frozen=True, kw_only=True)
class PrescriptionDispensed(DomainEvent):
    """Emitted when a validated prescription is dispensed (VALIDATED → DISPENSED)."""

    prescription_id: UUID
