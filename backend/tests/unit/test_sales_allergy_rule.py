"""Unit tests for the allergy-at-the-counter rule (pure domain).

Quyết định Đ-6 (Chain, 2026-07-30): warn plus a recorded acknowledgement, **not** a
hard block. Quyết định Đ-7: the warning is shown when a drug is added to the basket,
while the acknowledgement is enforced at completion — so both the "find" and the
"ensure" halves are exercised here independently.
"""

from __future__ import annotations

from uuid import UUID

import pytest

from pharmacy_os.modules.sales.domain import (
    AllergyAcknowledgementRequiredError,
    CustomerAllergy,
    DrugInfo,
    ensure_allergy_acknowledged,
    find_allergy_conflicts,
)

# Fixed ids so ordering assertions are reproducible: DRUG_A < DRUG_B and ING_1 < ING_2
# as UUIDs, which the rule's tie-breaker relies on.
DRUG_A = UUID("00000000-0000-0000-0000-0000000000a1")
DRUG_B = UUID("00000000-0000-0000-0000-0000000000b2")
ING_1 = UUID("00000000-0000-0000-0000-000000000011")
ING_2 = UUID("00000000-0000-0000-0000-000000000022")
ING_UNRELATED = UUID("00000000-0000-0000-0000-0000000000ff")


def _drug(drug_id: UUID, *ingredients: UUID) -> DrugInfo:
    return DrugInfo(
        drug_id=drug_id,
        requires_prescription=False,
        name="Thuốc thử",
        unit="viên",
        ingredient_ids=frozenset(ingredients),
    )


# --------------------------------------------------------------------------- find


def test_no_declared_allergy_yields_no_conflict() -> None:
    assert find_allergy_conflicts([_drug(DRUG_A, ING_1)], []) == []


def test_declared_allergy_on_unrelated_ingredient_yields_no_conflict() -> None:
    allergies = [CustomerAllergy(ingredient_id=ING_UNRELATED, severity="SEVERE")]
    assert find_allergy_conflicts([_drug(DRUG_A, ING_1)], allergies) == []


def test_matching_ingredient_is_reported_with_severity_and_note() -> None:
    allergies = [CustomerAllergy(ingredient_id=ING_1, severity="MODERATE", note="nổi mề đay")]
    conflicts = find_allergy_conflicts([_drug(DRUG_A, ING_1)], allergies)
    assert len(conflicts) == 1
    assert conflicts[0].drug_id == DRUG_A
    assert conflicts[0].ingredient_id == ING_1
    assert conflicts[0].severity == "MODERATE"
    assert conflicts[0].note == "nổi mề đay"


def test_drug_with_no_ingredients_recorded_never_conflicts() -> None:
    """A consumable (mask, thermometer) has no ingredients — and nobody is allergic
    to a thermometer. Guards the ``ingredient_ids`` default staying harmless."""
    plain = DrugInfo(drug_id=DRUG_A, requires_prescription=False)
    allergies = [CustomerAllergy(ingredient_id=ING_1, severity="SEVERE")]
    assert find_allergy_conflicts([plain], allergies) == []


def test_combination_drug_reports_every_matching_ingredient() -> None:
    """Two declared allergies inside one product must both surface — collapsing to
    one row per drug would hide the second reason (see ``AllergyConflict``)."""
    allergies = [
        CustomerAllergy(ingredient_id=ING_1, severity="MILD"),
        CustomerAllergy(ingredient_id=ING_2, severity="MILD"),
    ]
    conflicts = find_allergy_conflicts([_drug(DRUG_A, ING_1, ING_2)], allergies)
    assert [c.ingredient_id for c in conflicts] == [ING_1, ING_2]


def test_most_severe_conflict_comes_first() -> None:
    allergies = [
        CustomerAllergy(ingredient_id=ING_1, severity="MILD"),
        CustomerAllergy(ingredient_id=ING_2, severity="SEVERE"),
    ]
    # DRUG_A carries the MILD one and sorts first by id — severity must still win.
    conflicts = find_allergy_conflicts([_drug(DRUG_A, ING_1), _drug(DRUG_B, ING_2)], allergies)
    assert [c.severity for c in conflicts] == ["SEVERE", "MILD"]
    assert conflicts[0].drug_id == DRUG_B


def test_unknown_severity_still_conflicts_and_sorts_last() -> None:
    """A severity crm adds later must not crash the counter, and must not be silently
    dropped either — it ranks 0, so it still demands acknowledgement."""
    allergies = [
        CustomerAllergy(ingredient_id=ING_1, severity="ANAPHYLACTIC"),
        CustomerAllergy(ingredient_id=ING_2, severity="MILD"),
    ]
    conflicts = find_allergy_conflicts([_drug(DRUG_A, ING_1), _drug(DRUG_B, ING_2)], allergies)
    assert len(conflicts) == 2
    assert [c.severity for c in conflicts] == ["MILD", "ANAPHYLACTIC"]


def test_conflict_order_is_stable_across_input_order() -> None:
    """Same basket, drugs supplied in the other order — same output order."""
    allergies = [
        CustomerAllergy(ingredient_id=ING_1, severity="SEVERE"),
        CustomerAllergy(ingredient_id=ING_2, severity="SEVERE"),
    ]
    forward = find_allergy_conflicts([_drug(DRUG_A, ING_1), _drug(DRUG_B, ING_2)], allergies)
    backward = find_allergy_conflicts([_drug(DRUG_B, ING_2), _drug(DRUG_A, ING_1)], allergies)
    assert forward == backward


# ------------------------------------------------------------------------- ensure


def test_clean_order_needs_no_acknowledgement() -> None:
    ensure_allergy_acknowledged([], None)  # does not raise


def test_conflict_without_reason_is_blocked() -> None:
    conflicts = find_allergy_conflicts(
        [_drug(DRUG_A, ING_1)], [CustomerAllergy(ingredient_id=ING_1, severity="SEVERE")]
    )
    with pytest.raises(AllergyAcknowledgementRequiredError):
        ensure_allergy_acknowledged(conflicts, None)


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_blank_reason_does_not_count_as_acknowledgement(blank: str) -> None:
    """Đ-6 asks the seller to take responsibility in writing; whitespace is not
    writing. Without this, the gate is one keystroke of nothing away from useless."""
    conflicts = find_allergy_conflicts(
        [_drug(DRUG_A, ING_1)], [CustomerAllergy(ingredient_id=ING_1, severity="MILD")]
    )
    with pytest.raises(AllergyAcknowledgementRequiredError):
        ensure_allergy_acknowledged(conflicts, blank)


def test_recorded_reason_allows_the_sale() -> None:
    conflicts = find_allergy_conflicts(
        [_drug(DRUG_A, ING_1)], [CustomerAllergy(ingredient_id=ING_1, severity="SEVERE")]
    )
    ensure_allergy_acknowledged(conflicts, "Bác sĩ đã chỉ định, khách dùng nhiều lần không sao")


def test_error_message_names_the_worst_severity_and_the_count() -> None:
    """The counter needs to know *how bad* and *how many* from the message alone —
    the POS shows it verbatim when the confirm dialog is skipped."""
    allergies = [
        CustomerAllergy(ingredient_id=ING_1, severity="MILD"),
        CustomerAllergy(ingredient_id=ING_2, severity="SEVERE"),
    ]
    conflicts = find_allergy_conflicts([_drug(DRUG_A, ING_1), _drug(DRUG_B, ING_2)], allergies)
    with pytest.raises(AllergyAcknowledgementRequiredError) as err:
        ensure_allergy_acknowledged(conflicts, None)
    assert "2" in str(err.value)
    assert "SEVERE" in str(err.value)
