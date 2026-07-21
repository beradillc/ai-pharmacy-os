"""Sales domain rules (pure functions, framework-free)."""

from __future__ import annotations

from uuid import UUID

from pharmacy_os.modules.sales.domain.exceptions import PrescriptionRequiredError


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
