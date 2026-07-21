"""Prescription aggregate: :class:`Prescription` with its items and lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pharmacy_os.modules.prescription.domain.exceptions import (
    EmptyPrescriptionError,
    InvalidPrescriptionStateError,
)


def _now() -> datetime:
    return datetime.now(UTC)


class PrescriptionStatus(StrEnum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    DISPENSED = "DISPENSED"
    REJECTED = "REJECTED"


class PrescriptionSource(StrEnum):
    MANUAL = "MANUAL"
    IMAGE = "IMAGE"
    EPRESCRIPTION = "EPRESCRIPTION"


@dataclass(slots=True)
class PrescriptionItem:
    """One prescribed drug line. ``dose``/``frequency``/``duration`` are free-text, as written."""

    drug_id: UUID
    quantity: Decimal
    dose: str
    frequency: str
    duration: str
    instructions: str | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.quantity = Decimal(self.quantity)
        if self.quantity <= 0:
            raise ValueError("Số lượng thuốc trong đơn phải > 0")


@dataclass(slots=True)
class Prescription:
    """A patient's prescription (aggregate root).

    Lifecycle: ``DRAFT`` → ``VALIDATED`` → ``DISPENSED``, or ``DRAFT``/``VALIDATED``
    → ``REJECTED``. Items are fixed at creation — this module does not support
    editing a prescription's drug list after intake.
    """

    tenant_id: UUID
    branch_id: UUID
    customer_id: UUID
    doctor_name: str
    source: PrescriptionSource = PrescriptionSource.MANUAL
    doctor_license: str | None = None
    diagnosis: str | None = None
    image_url: str | None = None
    status: PrescriptionStatus = PrescriptionStatus.DRAFT
    validated_by: UUID | None = None
    rejection_reason: str | None = None
    items: list[PrescriptionItem] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)

    def _ensure_status(self, *allowed: PrescriptionStatus) -> None:
        if self.status not in allowed:
            raise InvalidPrescriptionStateError(
                f"Đơn không ở trạng thái cho phép (đang {self.status}, cần {allowed})"
            )

    def add_item(self, item: PrescriptionItem) -> None:
        self._ensure_status(PrescriptionStatus.DRAFT)
        self.items.append(item)

    def validate(self, validated_by: UUID) -> None:
        """Pharmacist approval: ``DRAFT`` → ``VALIDATED``. Requires at least one item."""
        self._ensure_status(PrescriptionStatus.DRAFT)
        if not self.items:
            raise EmptyPrescriptionError("Không thể xác thực đơn thuốc rỗng")
        self.validated_by = validated_by
        self.status = PrescriptionStatus.VALIDATED

    def reject(self, reason: str) -> None:
        """Reject — allowed from ``DRAFT`` (đơn không hợp lệ) or ``VALIDATED`` (rủi ro)."""
        self._ensure_status(PrescriptionStatus.DRAFT, PrescriptionStatus.VALIDATED)
        self.rejection_reason = reason
        self.status = PrescriptionStatus.REJECTED

    def dispense(self) -> None:
        """Cấp phát: ``VALIDATED`` → ``DISPENSED``."""
        self._ensure_status(PrescriptionStatus.VALIDATED)
        self.status = PrescriptionStatus.DISPENSED
