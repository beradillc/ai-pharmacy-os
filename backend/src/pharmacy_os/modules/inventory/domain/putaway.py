"""Cất hàng vào vị trí và chuyển giữa các vị trí — quy tắc thuần (BERAS V2 Phase 2).

🔴 Bất biến trung tâm của cả Phase 2, và là chỗ duy nhất hai sổ có thể lệch nhau:

    tổng hàng đã xếp vào các ô của một lô  ≤  tồn của lô đó

Vế phải là ``stock_balances`` — sổ **đã có từ trước**, nguồn sự thật về *có bao nhiêu*.
Vế trái là ``stock_at_location`` — sổ **mới**, trả lời *nằm ở đâu*. Hai sổ trả lời hai câu
hỏi khác nhau và cố ý **không** gộp: gộp lại là đổi hạt của projection đang chạy, thứ sẽ phá
FEFO, báo cáo và đề xuất nhập hàng cùng một lúc (xem ``INVENTORY_AUDIT.md`` mục 5.1).

Cái giá của việc tách: hàng **chưa xếp ô** là hợp lệ và bình thường — nó là hàng vừa nhận,
còn trên xe đẩy. Hệ thống phải nói ra được con số đó thay vì giả vờ mọi thứ đều có chỗ.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from pharmacy_os.modules.inventory.domain.exceptions import InsufficientStockError


class PutAwayError(Exception):
    """Base cho quy tắc cất hàng."""


class ExceedsBatchOnHandError(PutAwayError):
    """Xếp vào ô nhiều hơn số tồn thật của lô.

    Không phải lỗi làm tròn: nó nghĩa là **sổ vị trí đang nói dối** so với sổ tồn, và một
    khi đã lệch thì màn hình lấy hàng sẽ chỉ người ta tới một ô không có hàng.
    """


class LocationNotUsableError(PutAwayError):
    """Ô đã ngừng hoạt động, hoặc thuộc chi nhánh khác."""


@dataclass(frozen=True, slots=True)
class LocationStock:
    """Hàng của MỘT lô đang nằm ở MỘT ô."""

    location_id: UUID
    batch_id: UUID
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class PickCandidate:
    """Một chỗ có thể lấy hàng ra, kèm đủ thứ người đứng quầy cần đọc.

    Gộp cả ``expiry_date`` lẫn ``pick_order`` vào một chỗ vì hai con số đó **cùng quyết
    định** thứ tự lấy, và tách chúng ra hai nơi là mời người sau sắp xếp chỉ theo một nửa.
    """

    location_id: UUID
    location_path: str
    pick_order: int
    batch_id: UUID
    lot_no: str
    expiry_date: date
    quantity: Decimal


def ensure_can_put_away(
    *, dang_xep: Decimal, ton_cua_lo: Decimal, them: Decimal, o_dang_hoat_dong: bool
) -> None:
    """Kiểm trước khi xếp *them* đơn vị của một lô vào một ô.

    ``dang_xep`` là tổng đã xếp của lô đó **trên mọi ô**, không phải riêng ô đích: một lô
    trải nhiều ô là chuyện bình thường, và bất biến áp trên tổng chứ không trên từng ô.
    """
    if them <= 0:
        raise ValueError("Số lượng cất vào vị trí phải > 0")
    if not o_dang_hoat_dong:
        raise LocationNotUsableError("Ô đã ngừng hoạt động — không cất hàng vào được")
    if dang_xep + them > ton_cua_lo:
        raise ExceedsBatchOnHandError(
            f"Xếp {dang_xep + them} vượt tồn của lô ({ton_cua_lo}). "
            f"Đã xếp {dang_xep}, còn xếp được {max(ton_cua_lo - dang_xep, Decimal('0'))}"
        )


def chua_xep_o(*, ton_cua_lo: Decimal, dang_xep: Decimal) -> Decimal:
    """Số hàng của lô **chưa có chỗ** — vừa nhận, còn trên xe đẩy.

    Đây là con số phải hiện ra màn hình chứ không giấu đi: giấu nó là để người ta tin rằng
    mọi thứ trong kho đều đã có địa chỉ, và đó là lúc sổ vị trí bắt đầu nói dối trong im
    lặng.
    """
    return max(ton_cua_lo - dang_xep, Decimal("0"))


def sort_pick_candidates(candidates: list[PickCandidate]) -> list[PickCandidate]:
    """Sắp thứ tự lấy hàng: **FEFO trước, đường đi sau**.

    🔴 GĐ chốt 2026-07-31 (Chain uỷ quyền): *"FEFO thắng; vị trí chỉ quyết khi HSD bằng
    nhau."*

    An toàn thuốc không đánh đổi lấy vài bước chân — Điều 6.5 Luật Dược cấm bán thuốc quá
    hạn, và FEFO là cách hệ thống giữ điều đó. Nhưng khi hai lô **cùng hạn dùng** thì không
    còn lý do an toàn nào để chọn, lúc đó đi gần hơn là đúng.

    Khoá thứ ba là ``location_path`` để hai lượt gọi không bao giờ cho hai thứ tự khác nhau
    khi cả hạn dùng lẫn thứ tự đi đều bằng nhau.
    """
    return sorted(candidates, key=lambda c: (c.expiry_date, c.pick_order, c.location_path))


def allocate_from_locations(
    candidates: list[PickCandidate], demand: Decimal
) -> list[tuple[PickCandidate, Decimal]]:
    """Chia *demand* cho các chỗ theo thứ tự :func:`sort_pick_candidates`.

    Trả về danh sách ``(chỗ, số lượng lấy)`` — một lượt lấy hàng trải nhiều ô là bình thường
    và phải nói ra được từng ô, nếu không người đi lấy sẽ đứng trước một ô thiếu hàng mà
    không biết phần còn lại ở đâu.

    Raises :class:`InsufficientStockError` nếu tổng các chỗ **đã xếp ô** không đủ. Lưu ý:
    thiếu ở đây **không** có nghĩa là kho hết hàng — có thể hàng còn nhưng chưa ai xếp vào ô
    (xem :func:`chua_xep_o`). Bên gọi phải phân biệt hai chuyện đó khi hiện lỗi.
    """
    if demand <= 0:
        raise ValueError("Số lượng lấy phải > 0")

    ordered = [c for c in sort_pick_candidates(candidates) if c.quantity > 0]
    total = sum((c.quantity for c in ordered), Decimal("0"))
    if total < demand:
        raise InsufficientStockError(requested=demand, available=total)

    ket_qua: list[tuple[PickCandidate, Decimal]] = []
    con_lai = demand
    for c in ordered:
        if con_lai <= 0:
            break
        lay = min(c.quantity, con_lai)
        ket_qua.append((c, lay))
        con_lai -= lay
    return ket_qua
