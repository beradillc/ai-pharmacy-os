"""Sales domain exceptions (pure — no framework)."""

from __future__ import annotations


class SalesError(Exception):
    """Base for sales domain rule violations."""


class EmptyOrderError(SalesError):
    """Raised when completing an order that has no lines."""


class PrescriptionRequiredError(SalesError):
    """Raised when selling a prescription drug (ETC/CONTROLLED) without a valid Rx."""


class InvalidPrescriptionRefError(SalesError):
    """Raised when a sale's ``prescription_ref`` is not a real, sale-authorising Rx.

    Distinct from :class:`PrescriptionRequiredError` (which means *no* ref at all):
    here a ref was supplied but the referenced prescription does not exist for the
    tenant, or is not in a state that authorises selling its ETC items.
    """


class InvalidOrderStateError(SalesError):
    """Raised on an operation not allowed in the order's current status."""


class UnderpaidError(SalesError):
    """Raised when recorded payments do not cover the order subtotal."""


class InvalidReturnError(SalesError):
    """Raised when a return references an unknown line or an impossible quantity."""


class AllergyAcknowledgementRequiredError(SalesError):
    """Raised when completing a sale that collides with a declared allergy without
    the seller recording a reason for dispensing anyway.

    Not a prohibition — quyết định Đ-6 chose *warn plus acknowledgement* over a hard
    block, so supplying a reason clears this. See
    :func:`~pharmacy_os.modules.sales.domain.rules.ensure_allergy_acknowledged` for
    why the gate sits at completion time rather than where the warning is shown.
    """


class PriceOverrideReasonRequiredError(SalesError):
    """Đơn bán lệch giá niêm yết mà chưa ghi lý do.

    Quyết định của Chain (2026-07-31): **cho lệch cả hai chiều, đòi lý do, ghi audit.**

    GĐ đã nêu tại phiên đó rằng Điều 6.5.i Luật Dược cấm bán **cao hơn** giá niêm yết
    nên đề nghị làm bất đối xứng (cao hơn ⇒ chặn hẳn); Chain giữ nguyên phương án đối
    xứng. Ghi lại ở đây vì lớp mã này là nơi quyết định đó có hiệu lực — xem
    ``docs/features/gia-ban-va-thu-tien-quay/01_DECISIONS.md`` mục cờ pháp lý.
    """


class UnknownDrugError(SalesError):
    """Đơn tham chiếu một ``drug_id`` không có trong danh mục của nhà thuốc.

    **Phương án B** (GĐ chọn 2026-07-31 dưới uỷ quyền của Chain; ba phương án ở
    PROJECT_STATE §7cl): từ chối ở **đơn mới**, giữ khoan dung cho **đường đồng bộ**.

    Vì sao không chặn cả hai: một đơn đã xếp hàng offline có thể mang mã thuốc đã bị gỡ
    khỏi danh mục **sau khi bán**. Siết ở đó là đổi một lỗi im lặng (sổ sách lệch tồn kho)
    lấy một lỗi mất tiền (đơn đã bán không đồng bộ được nữa) — mà đơn đã bán rồi thì tiền
    đã vào két, hàng đã ra khỏi kệ.

    Vì sao không giữ nguyên cả hai: ở đơn **mới**, một `drug_id` lạ chỉ có thể là máy khách
    sai. Đơn vẫn tạo, **doanh thu vẫn ghi nhận**, nhưng không trừ tồn kho nào ⇒ sổ sách
    lệch tồn kho, im lặng, trong đường tiền.
    """
