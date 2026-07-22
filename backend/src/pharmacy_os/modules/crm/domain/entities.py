"""CRM aggregate: :class:`Customer` and its clinical/history sub-entities.

``Customer`` is deliberately independent of ``compliance.CustomerDetail`` (the
Phụ lục XXI ledger snapshot): that value object has no identity and is scoped to a
single controlled-substance ledger row at the moment of sale, while ``Customer`` here
is tenant-owned master data with its own id, reused across sales/clinical checks.
Linking the two (if ever needed) is a cross-module composition-root decision for a
later step, not a domain concern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pharmacy_os.modules.crm.domain.exceptions import (
    DuplicateAllergyError,
    DuplicateConditionError,
    InvalidConditionError,
    InvalidCustomerError,
    InvalidMedicationHistoryEntryError,
)


class AllergySeverity(StrEnum):
    """Clinical severity of a recorded allergy."""

    MILD = "MILD"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"


class MedicationHistorySource(StrEnum):
    """Where a medication-history entry originated (cross-module ref, not FK)."""

    SALE = "SALE"
    PRESCRIPTION = "PRESCRIPTION"


@dataclass(slots=True)
class Allergy:
    """A known allergy, keyed by active ingredient — not by free-text drug name.

    Ingredient-based so it can be matched against :class:`DrugInteraction`-style
    ingredient checks later (catalog Sprint 6 Bước 1), the same way clinical
    interactions are keyed, rather than against a specific branded product.
    """

    ingredient_id: UUID
    severity: AllergySeverity
    note: str | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class Condition:
    """A pre-existing condition (bệnh nền), coded per ICD-10."""

    condition_code: str
    note: str | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.condition_code.strip():
            raise InvalidConditionError("Mã bệnh nền (ICD-10) không được để trống")


@dataclass(slots=True)
class MedicationHistoryEntry:
    """One past dispense/sale fact for a customer — minimal, cross-module ref only.

    ``ref_id`` points at the originating ``SalesOrder``/``Prescription`` (by
    ``source``); it is a plain UUID reference, not a FK, matching the
    ``ref_type``/``ref_id`` convention already used by ``inventory.StockMovement``.
    Populating this from live sale/dispense events is a later, cross-module step —
    here it is only the shape a use-case can append to.
    """

    drug_id: UUID
    quantity: Decimal
    source: MedicationHistorySource
    ref_id: UUID
    occurred_at: datetime
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.quantity = Decimal(self.quantity)
        if self.quantity <= 0:
            raise InvalidMedicationHistoryEntryError("Số lượng dùng thuốc phải > 0")


@dataclass(slots=True)
class Customer:
    """Customer/patient master record (aggregate root). Not tenant-scoped here —
    tenant/branch ownership is attached at the repository boundary, like ``Drug``.
    """

    full_name: str
    phone: str | None = None
    dob: date | None = None
    gender: str | None = None
    weight_kg: Decimal | None = None
    national_id_hash: str | None = None
    id: UUID = field(default_factory=uuid4)
    allergies: list[Allergy] = field(default_factory=list)
    conditions: list[Condition] = field(default_factory=list)
    history: list[MedicationHistoryEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.full_name.strip():
            raise InvalidCustomerError("Họ tên khách hàng không được để trống")
        if self.weight_kg is not None:
            self.weight_kg = Decimal(self.weight_kg)
            if self.weight_kg <= 0:
                raise InvalidCustomerError("Cân nặng phải > 0")

    def add_allergy(self, allergy: Allergy) -> None:
        if any(a.ingredient_id == allergy.ingredient_id for a in self.allergies):
            raise DuplicateAllergyError("Dị ứng với hoạt chất này đã được ghi nhận")
        self.allergies.append(allergy)

    def add_condition(self, condition: Condition) -> None:
        if any(c.condition_code == condition.condition_code for c in self.conditions):
            raise DuplicateConditionError("Bệnh nền này đã được ghi nhận")
        self.conditions.append(condition)

    def record_history_entry(self, entry: MedicationHistoryEntry) -> None:
        self.history.append(entry)

    def has_allergy_to(self, ingredient_id: UUID) -> bool:
        return any(a.ingredient_id == ingredient_id for a in self.allergies)
