"""Unit tests for the S5.4 sale-authorising prescription rule (pure domain)."""

from __future__ import annotations

import pytest

from pharmacy_os.modules.sales.domain import (
    InvalidPrescriptionRefError,
    ensure_prescription_valid_for_sale,
)


@pytest.mark.parametrize("status", ["VALIDATED", "DISPENSED"])
def test_sale_authorising_states_pass(status: str) -> None:
    ensure_prescription_valid_for_sale(status)  # does not raise


@pytest.mark.parametrize("status", ["DRAFT", "REJECTED"])
def test_non_authorising_states_blocked(status: str) -> None:
    with pytest.raises(InvalidPrescriptionRefError):
        ensure_prescription_valid_for_sale(status)


def test_missing_prescription_blocked() -> None:
    # None = no prescription exists for the tenant with that ref id.
    with pytest.raises(InvalidPrescriptionRefError):
        ensure_prescription_valid_for_sale(None)
