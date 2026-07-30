"""Sales domain rules (pure functions, framework-free)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from pharmacy_os.modules.sales.domain.exceptions import (
    AllergyAcknowledgementRequiredError,
    InvalidPrescriptionRefError,
    PrescriptionRequiredError,
)

if TYPE_CHECKING:  # pragma: no cover — types only, see note below
    from pharmacy_os.modules.sales.domain.ports import CustomerAllergy, DrugInfo

# Type-only import on purpose: ``ports`` imports ``SalesOrder`` from ``entities``, and
# ``entities`` imports ``ensure_rx_for_etc`` from this module — importing ``ports`` at
# runtime here would close that loop. The rule functions below only read attributes
# (``ingredient_ids``, ``ingredient_id``, ``severity``), so they need the names for
# annotations and nothing more. ``from __future__ import annotations`` (above) keeps
# those annotations as strings at runtime.

# States of a referenced prescription that authorise selling its ETC items.
# VALIDATED = pharmacist-approved; DISPENSED = already handed over (still a
# legitimate authorisation, and accepting it avoids coupling the order of
# "dispense prescription" vs "complete sale"). DRAFT/REJECTED are blocked.
_SALE_AUTHORISING_RX_STATES = frozenset({"VALIDATED", "DISPENSED"})


def ensure_rx_for_etc(requires_prescription: bool, prescription_ref: UUID | None) -> None:
    """Block completing a sale of a prescription drug without a valid Rx reference.

    ``requires_prescription`` is an authoritative flag about the order's items
    (ETC/CONTROLLED per :meth:`Drug.is_prescription_required`), supplied to the
    domain rather than looked up here — sales never imports catalog.
    """
    if requires_prescription and prescription_ref is None:
        raise PrescriptionRequiredError(
            "Thuốc kê đơn (ETC/kiểm soát) cần đơn thuốc hợp lệ mới được bán"
        )


def ensure_prescription_valid_for_sale(status: str | None) -> None:
    """Verify a referenced prescription really authorises the ETC sale.

    ``status`` is the referenced prescription's raw status value, or ``None`` when
    no prescription exists for the tenant with that id. Only applied when the order
    has ETC items and a ``prescription_ref`` — and only when a
    ``PrescriptionInfoProvider`` is wired (else sales keeps the ref-present-only
    rule of :func:`ensure_rx_for_etc`).
    """
    if status is None:
        raise InvalidPrescriptionRefError(
            "prescription_ref không trỏ tới đơn thuốc có thật của cơ sở"
        )
    if status not in _SALE_AUTHORISING_RX_STATES:
        raise InvalidPrescriptionRefError(
            f"Đơn thuốc chưa cho phép bán (trạng thái {status}; cần đã duyệt/đã cấp phát)"
        )


# Ordering used only to put the most dangerous conflict first when several are
# found on one order — sales owns this ranking the same way it owns
# `_SALE_AUTHORISING_RX_STATES`, rather than importing the crm enum. A value not
# listed here (a severity crm adds later) ranks 0: it still produces a conflict and
# still demands acknowledgement, it just sorts last instead of crashing.
_ALLERGY_SEVERITY_RANK: dict[str, int] = {"SEVERE": 3, "MODERATE": 2, "MILD": 1}


@dataclass(frozen=True, slots=True)
class AllergyConflict:
    """One drug on the order carries one ingredient the customer reacts to.

    Per *ingredient*, not per drug: a combination product can collide with two
    separate declared allergies, and the counter needs to see both — collapsing
    them to one row per drug would hide the second reason.
    """

    drug_id: UUID
    ingredient_id: UUID
    severity: str
    note: str | None = None


def find_allergy_conflicts(
    drugs: Iterable[DrugInfo], allergies: Iterable[CustomerAllergy]
) -> list[AllergyConflict]:
    """Match the order's drugs against the customer's declared allergies.

    Pure set intersection on ingredient ids — no lookup, no I/O. Both sides are
    supplied by the caller (``DrugInfoProvider`` and ``CustomerAllergyProvider``),
    so this stays a decision function that a unit test can drive directly.

    Returns conflicts ordered most-severe first, then by drug then ingredient id, so
    the counter always sees the same order for the same basket and a test can assert
    on position. An empty result means *checked and clean* — it does **not** mean
    "not checked"; that case is carried by
    :attr:`CustomerAllergyProfile.consent_granted` and must be handled by the caller.
    """
    declared = {a.ingredient_id: a for a in allergies}
    if not declared:
        return []
    conflicts = [
        AllergyConflict(
            drug_id=drug.drug_id,
            ingredient_id=ingredient_id,
            severity=declared[ingredient_id].severity,
            note=declared[ingredient_id].note,
        )
        for drug in drugs
        for ingredient_id in sorted(drug.ingredient_ids & declared.keys())
    ]
    conflicts.sort(
        key=lambda c: (-_ALLERGY_SEVERITY_RANK.get(c.severity, 0), c.drug_id, c.ingredient_id)
    )
    return conflicts


def ensure_allergy_acknowledged(
    conflicts: Iterable[AllergyConflict], acknowledgement: str | None
) -> None:
    """Block completing a sale that collides with a declared allergy unless the
    seller has explicitly taken responsibility, in writing.

    Quyết định Đ-6 (Chain, 2026-07-30): **warn, do not hard-block**. A pharmacist
    may have a sound reason to dispense anyway — a mild reaction, no substitute in
    stock, a prescriber who already weighed it up. A hard block would push counter
    staff into not recording allergies at all, or into leaving the customer off the
    order, which destroys the record this warning depends on.

    So the gate is an acknowledgement, not a prohibition: a non-blank reason. The
    caller audits it (``SALES_ALLERGY_WARNING_OVERRIDDEN``); this function only
    decides whether one was required and supplied.

    **This is the enforcement point, and it is deliberately at completion time even
    though the warning is shown when the drug is added to the basket (Đ-7).** A check
    that only ran while building the basket would be advisory only — a client could
    skip it, or the basket could change after it passed. Re-deciding here, on the
    server, from the order that is actually being completed, is what gives Đ-6 teeth.
    """
    pending = list(conflicts)
    if not pending:
        return
    if acknowledgement is None or not acknowledgement.strip():
        worst = pending[0]
        raise AllergyAcknowledgementRequiredError(
            f"Đơn có {len(pending)} cảnh báo dị ứng (nặng nhất: {worst.severity}). "
            "Phải ghi lý do xác nhận vẫn bán mới hoàn tất được."
        )
