"""Sales domain rules (pure functions, framework-free)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from pharmacy_os.modules.sales.domain.exceptions import (
    AllergyAcknowledgementRequiredError,
    InvalidPrescriptionRefError,
    PrescriptionRequiredError,
    PriceOverrideReasonRequiredError,
)

if TYPE_CHECKING:  # pragma: no cover — types only, see note below
    from pharmacy_os.modules.sales.domain.ports import AllergyRisk

# Type-only import on purpose: ``ports`` imports ``SalesOrder`` from ``entities``, and
# ``entities`` imports ``ensure_rx_for_etc`` from this module — importing ``ports`` at
# runtime here would close that loop. The rule function below only reads attributes
# (``conflict_count``, ``worst_severity``), so it needs the name for the annotation and
# nothing more. ``from __future__ import annotations`` (above) keeps
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


def ensure_allergy_acknowledged(risk: AllergyRisk | None, acknowledgement: str | None) -> None:
    """Block completing a sale that collides with a declared allergy unless the seller
    has explicitly taken responsibility, in writing.

    Quyết định Đ-6 (Chain, 2026-07-30): **warn, do not hard-block**. A pharmacist may
    have a sound reason to dispense anyway — a mild reaction, no substitute in stock, a
    prescriber who already weighed it up. A hard block would push counter staff into not
    recording allergies at all, or into leaving the customer off the order, which
    destroys the record this warning depends on.

    So the gate is an acknowledgement, not a prohibition: a non-blank reason. The caller
    audits it (``SALES_ALLERGY_WARNING_OVERRIDDEN``); this function only decides whether
    one was required and supplied.

    **This is the enforcement point, and it is deliberately at completion time even
    though the warning is shown when the drug is added to the basket (Đ-7).** A check
    that only ran while building the basket would be advisory only — a client could skip
    it, or the basket could change after it passed. Re-deciding here, on the server,
    from the order that is actually being completed, is what gives Đ-6 teeth.

    ``risk is None`` (no customer named on the order, or the record is gone) and
    ``conflict_count == 0`` both pass: there is nothing to acknowledge. A basket the
    pharmacy was not allowed to check (``consent_granted=False``) also passes — refusing
    to sell because consent for health data is absent would punish the customer for
    exercising a right, and no conflict is known to exist.
    """
    if risk is None or risk.conflict_count == 0:
        return
    if acknowledgement is None or not acknowledgement.strip():
        nang_nhat = risk.worst_severity or "không rõ mức độ"
        raise AllergyAcknowledgementRequiredError(
            f"Đơn có {risk.conflict_count} cảnh báo dị ứng (nặng nhất: {nang_nhat}). "
            "Phải ghi lý do xác nhận vẫn bán mới hoàn tất được."
        )


def ensure_price_override_acknowledged(deviation_count: int, acknowledgement: str | None) -> None:
    """Chặn hoàn tất một đơn bán lệch giá niêm yết khi chưa ghi lý do.

    Cùng khuôn với :func:`ensure_allergy_acknowledged`, và cùng lý do: cổng là một lời
    **xác nhận có chữ**, không phải một lệnh cấm. Thu ngân có lý do chính đáng để bán
    lệch — khuyến mãi, làm tròn tiền lẻ, giá thoả thuận với khách quen, mã vừa đổi giá
    mà kệ chưa kịp dán lại. Cấm cứng sẽ đẩy quầy sang chỗ tệ hơn: bán bằng một mã khác,
    hoặc không cập giá niêm yết nữa để khỏi bị chặn — và khi đó chính giá niêm yết,
    thứ Điều 107.4 đòi, mới là cái hỏng.

    **Điểm cưỡng chế đặt ở lúc hoàn tất đơn, trên máy chủ**, giống Đ-6: một phép kiểm
    chỉ chạy lúc thêm hàng vào giỏ là lời khuyên, không phải cổng — máy khách bỏ qua
    được, và giỏ hàng đổi sau khi nó đã cho qua.

    ``deviation_count == 0`` đi thẳng: không có gì để giải thích. Mã **chưa đặt giá
    niêm yết** không tính là lệch — xem ``DrugInfo.sale_price``.
    """
    if deviation_count == 0:
        return
    if acknowledgement is None or not acknowledgement.strip():
        raise PriceOverrideReasonRequiredError(
            f"Đơn có {deviation_count} dòng bán lệch giá niêm yết. "
            "Phải ghi lý do mới hoàn tất được."
        )
