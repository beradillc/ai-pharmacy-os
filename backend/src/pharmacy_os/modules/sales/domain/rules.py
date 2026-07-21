"""Sales domain rules (pure functions, framework-free)."""

from __future__ import annotations

from uuid import UUID

from pharmacy_os.modules.sales.domain.exceptions import (
    InvalidPrescriptionRefError,
    PrescriptionRequiredError,
)

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
