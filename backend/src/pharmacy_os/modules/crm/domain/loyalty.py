"""Tích luỹ chi tiêu trong năm và các mốc thưởng (Đ-5, Chain chốt 2026-07-29).

Ghi **tiền**, không ghi "điểm". Chain phát biểu chương trình bằng đồng — *"tích 1
triệu tặng bịch khẩu trang"* — nên phát minh một đơn vị điểm rồi quy đổi 1 điểm =
1 đồng chỉ thêm một lớp để sai, và thêm một câu hỏi ở quầy: *"1 điểm là bao nhiêu
tiền?"*.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pharmacy_os.modules.crm.domain.exceptions import CrmError


class LoyaltyError(CrmError):
    """Sai sót nghiệp vụ trong sổ tích luỹ."""


class DuplicateAccrualError(LoyaltyError):
    """Một đơn hàng được cộng vào sổ hai lần."""


class RewardAlreadyGrantedError(LoyaltyError):
    """Một mốc thưởng đã trao rồi lại trao lần nữa trong cùng năm."""


class RewardNotEarnedError(LoyaltyError):
    """Trao thưởng khi chưa tích đủ mốc."""


class RewardTier(StrEnum):
    """Hai mốc thưởng. Giá trị enum mang luôn con số để không ai phải tra bảng."""

    ONE_MILLION = "ONE_MILLION"
    THREE_MILLION = "THREE_MILLION"


#: Ngưỡng của từng mốc, bằng đồng.
#:
#: Để ở đây chứ không ở bảng cấu hình vì đây là **chương trình đang chạy với khách
#: thật**: đổi ngưỡng giữa chừng là đổi lời hứa đã nói với người ta, nên nó phải là
#: một thay đổi mã có commit, có người duyệt — không phải một ô nhập ai cũng sửa được.
TIER_THRESHOLDS: dict[RewardTier, Decimal] = {
    RewardTier.ONE_MILLION: Decimal("1000000"),
    RewardTier.THREE_MILLION: Decimal("3000000"),
}


def tiers_reached(accrued: Decimal) -> frozenset[RewardTier]:
    """Những mốc mà mức tích luỹ này đã chạm tới.

    **Cộng dồn, không thay thế** (Chain chốt): đạt 3 triệu thì được **cả hai** —
    đi qua mốc 1 triệu nhận quà mốc đó, đi tiếp tới 3 triệu nhận thêm quà mốc 3
    triệu. Không ai cảm thấy bị mất phần đã đạt được.
    """
    return frozenset(t for t, nguong in TIER_THRESHOLDS.items() if accrued >= nguong)


@dataclass(slots=True)
class AccrualEntry:
    """Một lần cộng tiền vào sổ, ứng với đúng một đơn hàng.

    Sổ **chỉ ghi thêm**. Sửa sai bằng **bút toán đảo** (`amount` âm), không UPDATE
    và không DELETE — người sau đọc sổ này để trả lời *"vì sao khách được nhận
    quà"*, và một dòng bị xoá lặng lẽ là câu trả lời biến mất.

    🔴 **Không mang `drug_id`** (quyết định Đ-3). Chỉ `order_id` + số tiền. Nếu sổ
    mang mã thuốc thì một bảng vốn để đếm tiền trở thành **hồ sơ bệnh án**, và
    người có quyền xem tích luỹ (thu ngân) đọc được bệnh của khách.
    """

    customer_id: UUID
    order_id: UUID
    amount: Decimal
    occurred_at: datetime
    #: Bút toán đảo trỏ về dòng bị đảo — để đối chiếu, không phải để xoá nó.
    reverses_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.amount == 0:
            raise LoyaltyError("Bút toán tích luỹ không được bằng 0")
        if self.occurred_at.tzinfo is None:
            raise LoyaltyError("Thời điểm tích luỹ phải có múi giờ")


@dataclass(slots=True)
class RewardGrant:
    """Một lần trao quà cho một mốc, trong một năm.

    Khoá duy nhất là **(khách, năm, mốc)** — đó chính là quy tắc *"một lần mỗi
    mốc, mỗi năm"* của Chain, đặt ở chỗ không đi vòng được thay vì tin vào giao
    diện nhớ hộ.
    """

    customer_id: UUID
    year: int
    tier: RewardTier
    granted_at: datetime
    granted_by: UUID | None = None
    #: Mã hàng đã trao. Quà là **hàng thật rời khỏi kho thật**, nên phải ghi lại
    #: đã cho cái gì — không thì tồn kho lệch mà không ai lần ra vì sao.
    drug_id: UUID | None = None
    note: str | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class YearlyLoyalty:
    """Tình trạng tích luỹ của một khách trong **một năm dương lịch**.

    Năm dương lịch, reset 01/01 (Chain chốt): dễ nói với khách và trùng kỳ báo cáo
    kế toán. Cửa sổ trượt 12 tháng công bằng hơn nhưng số tích luỹ **tự giảm** khi
    đơn cũ rơi ra khỏi cửa sổ — khách nhìn thấy con số đi lùi mà không hiểu vì sao.
    """

    customer_id: UUID
    year: int
    entries: list[AccrualEntry] = field(default_factory=list)
    grants: list[RewardGrant] = field(default_factory=list)

    @property
    def accrued(self) -> Decimal:
        """Tổng tích luỹ. Bút toán đảo mang số âm nên tự trừ ra."""
        return sum((e.amount for e in self.entries), Decimal("0"))

    def accrue(self, entry: AccrualEntry) -> None:
        """Cộng một đơn vào sổ.

        🔴 Chặn cộng trùng theo `order_id`. Sự kiện bán hàng **được gửi lại** khi
        outbox thử lại — không chặn ở đây thì một đơn 3 triệu cộng hai lần là khách
        chạm mốc bằng tiền không có thật (rủi ro R-1 trong bản thiết kế).
        Bút toán đảo được phép trùng `order_id` vì nó chính là dòng đối ứng.
        """
        if entry.reverses_id is None and any(
            e.order_id == entry.order_id and e.reverses_id is None for e in self.entries
        ):
            raise DuplicateAccrualError(f"Đơn hàng {entry.order_id} đã được cộng vào sổ rồi")
        self.entries.append(entry)

    def reverse(self, entry_id: UUID, at: datetime | None = None) -> AccrualEntry:
        """Đảo một bút toán — dùng khi huỷ đơn hoặc trả hàng (rủi ro R-2).

        Sinh một dòng MỚI mang số âm. Không sửa dòng cũ: câu hỏi *"tháng trước khách
        có đủ mốc không"* chỉ trả lời được nếu lịch sử còn nguyên.
        """
        goc = next((e for e in self.entries if e.id == entry_id), None)
        if goc is None:
            raise LoyaltyError(f"Không có bút toán {entry_id} trong sổ")
        if goc.reverses_id is not None:
            raise LoyaltyError("Không đảo một bút toán đảo")
        if any(e.reverses_id == entry_id for e in self.entries):
            raise LoyaltyError(f"Bút toán {entry_id} đã được đảo rồi")
        dao = AccrualEntry(
            customer_id=goc.customer_id,
            order_id=goc.order_id,
            amount=-goc.amount,
            occurred_at=at or datetime.now(UTC),
            reverses_id=goc.id,
        )
        self.entries.append(dao)
        return dao

    def granted_tiers(self) -> frozenset[RewardTier]:
        return frozenset(g.tier for g in self.grants)

    def pending_tiers(self) -> frozenset[RewardTier]:
        """Mốc đã tích đủ nhưng **chưa trao quà** — thứ quầy cần nhìn thấy."""
        return tiers_reached(self.accrued) - self.granted_tiers()

    def grant(self, grant: RewardGrant) -> None:
        """Ghi nhận đã trao quà một mốc.

        Hai phép kiểm, và cả hai đều đặt ở domain chứ không ở giao diện:
        **chưa đủ mốc thì không trao**, và **một mốc chỉ trao một lần mỗi năm**.
        Đây là chỗ hàng thật rời kho, nên nó phải chặt ở nơi mọi đường đều đi qua.
        """
        if grant.tier not in tiers_reached(self.accrued):
            nguong = TIER_THRESHOLDS[grant.tier]
            raise RewardNotEarnedError(
                f"Chưa đủ mốc {nguong:,.0f} đ — mới tích {self.accrued:,.0f} đ"
            )
        if grant.tier in self.granted_tiers():
            raise RewardAlreadyGrantedError(f"Mốc {grant.tier} đã trao trong năm {self.year} rồi")
        self.grants.append(grant)
