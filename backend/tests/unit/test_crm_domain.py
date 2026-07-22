"""Unit tests for the crm domain: Customer aggregate, allergies, conditions, history."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from pharmacy_os.modules.crm.domain import (
    Allergy,
    AllergySeverity,
    Condition,
    Customer,
    DuplicateAllergyError,
    DuplicateConditionError,
    InvalidConditionError,
    InvalidCustomerError,
    InvalidMedicationHistoryEntryError,
    MedicationHistoryEntry,
    MedicationHistorySource,
)


def _customer(**overrides: object) -> Customer:
    defaults: dict[str, object] = {"full_name": "Nguyễn Văn A"}
    defaults.update(overrides)
    return Customer(**defaults)  # type: ignore[arg-type]


# --- Customer ----------------------------------------------------------------


def test_blank_name_rejected() -> None:
    with pytest.raises(InvalidCustomerError):
        _customer(full_name="   ")


def test_non_positive_weight_rejected() -> None:
    with pytest.raises(InvalidCustomerError):
        _customer(weight_kg=Decimal("0"))


def test_customer_defaults_have_empty_collections() -> None:
    c = _customer()
    assert c.allergies == []
    assert c.conditions == []
    assert c.history == []


# --- Allergy (ingredient-based, not free-text drug name) ----------------------


def test_add_allergy_ingredient_based() -> None:
    c = _customer()
    penicillin = uuid4()
    c.add_allergy(Allergy(ingredient_id=penicillin, severity=AllergySeverity.SEVERE))
    assert c.has_allergy_to(penicillin) is True
    assert c.has_allergy_to(uuid4()) is False


def test_duplicate_allergy_same_ingredient_rejected() -> None:
    c = _customer()
    penicillin = uuid4()
    c.add_allergy(Allergy(ingredient_id=penicillin, severity=AllergySeverity.MILD))
    with pytest.raises(DuplicateAllergyError):
        c.add_allergy(Allergy(ingredient_id=penicillin, severity=AllergySeverity.SEVERE))


# --- Condition (bệnh nền, ICD-10) ---------------------------------------------


def test_condition_requires_code() -> None:
    with pytest.raises(InvalidConditionError):
        Condition(condition_code="   ")


def test_add_condition_and_reject_duplicate_code() -> None:
    c = _customer()
    c.add_condition(Condition(condition_code="E11", note="Đái tháo đường type 2"))
    assert c.conditions[0].condition_code == "E11"
    with pytest.raises(DuplicateConditionError):
        c.add_condition(Condition(condition_code="E11"))


# --- MedicationHistoryEntry (minimal, cross-module ref only) ------------------


def test_medication_history_quantity_must_be_positive() -> None:
    with pytest.raises(InvalidMedicationHistoryEntryError):
        MedicationHistoryEntry(
            drug_id=uuid4(),
            quantity=Decimal("0"),
            source=MedicationHistorySource.SALE,
            ref_id=uuid4(),
            occurred_at=datetime.now(UTC),
        )


def test_record_history_entry_appends() -> None:
    c = _customer()
    entry = MedicationHistoryEntry(
        drug_id=uuid4(),
        quantity=Decimal("2"),
        source=MedicationHistorySource.PRESCRIPTION,
        ref_id=uuid4(),
        occurred_at=datetime.now(UTC),
    )
    c.record_history_entry(entry)
    assert c.history == [entry]
