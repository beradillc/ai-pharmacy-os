"""Tích luỹ chi tiêu trong năm và quà thưởng (Đ-9, Chain chốt 2026-07-30).

Ghi **tiền**, không ghi "điểm". Chain phát biểu chương trình bằng đồng — *"cứ mỗi
khi đủ 2 triệu, 1 hộp khẩu trang"* — nên phát minh một đơn vị điểm rồi quy đổi
1 điểm = 1 đồng chỉ thêm một lớp để sai, và thêm một câu hỏi ở quầy: *"1 điểm là
bao nhiêu tiền?"*.

**Đ-9 THAY Đ-5 về cấu trúc mốc.** Đ-5 (29/07) là *hai mốc một lần mỗi năm* — 1 triệu
tặng bịch, 3 triệu tặng hộp. Đ-9 (30/07) là **một bậc lặp lại**: mỗi 2 triệu tích luỹ
trong năm dương lịch được 1 hộp, không giới hạn số lần. Nên mô hình đổi từ **tập hợp
mốc** sang **số đếm**: câu hỏi không còn là *"đã chạm mốc nào"* mà là *"được bao nhiêu
hộp, đã trao bao nhiêu"*.

Đo trước khi chốt (`nt650v2`, 59 ngày, 12 khách): trung bình 1.938.533 đ/khách ⇒ ước
11.992.621 đ/khách/năm ⇒ **5,5 hộp/khách/năm** = 192.500 đ, tức **1,61 % doanh thu**.
Gấp 2,75 lần Đ-5 nhưng vẫn trong mức thường của chương trình khách quen (1–2 %).

Giữ nguyên từ Đ-5: **năm dương lịch** (reset 01/01) và cách ghi sổ chỉ-thêm bằng bút
toán đảo. Phần tiền vào không đổi; chỉ nửa phần thưởng viết lại.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pharmacy_os.modules.crm.domain.exceptions import CrmError


class LoyaltyError(CrmError):
    """Sai sót nghiệp vụ trong sổ tích luỹ."""


class DuplicateAccrualError(LoyaltyError):
    """Một đơn hàng được cộng vào sổ hai lần."""


class RewardAlreadyGrantedError(LoyaltyError):
    """Trao quà khi đã trao hết số hộp khách được hưởng, hoặc trao trùng số thứ tự."""


class RewardNotEarnedError(LoyaltyError):
    """Trao thưởng khi chưa tích đủ bậc 2 triệu tiếp theo."""


#: Mỗi bao nhiêu đồng tích luỹ thì được 1 hộp khẩu trang (Đ-9).
#:
#: Để ở đây chứ không ở bảng cấu hình vì đây là **chương trình đang chạy với khách
#: thật**: đổi bậc giữa chừng là đổi lời hứa đã nói với người ta, nên nó phải là một
#: thay đổi mã có commit, có người duyệt — không phải một ô nhập ai cũng sửa được.
REWARD_STEP: Decimal = Decimal("2000000")


def boxes_earned(accrued: Decimal) -> int:
    """Số hộp mức tích luỹ này được hưởng — **lặp lại**, không có trần.

    Chia lấy phần nguyên: 2 triệu được 1 hộp, 5,9 triệu được 2 hộp, 25 triệu được 12.
    Đúng 2 triệu là đạt bậc (``>=``), không phải "hơn 2 triệu".

    Tích luỹ âm (sổ bị đảo nhiều hơn cộng) trả **0**, không trả số âm: số hộp được
    hưởng là một phép đếm, và một phép đếm âm không có nghĩa gì ở quầy.
    """
    if accrued < REWARD_STEP:
        return 0
    return int(accrued // REWARD_STEP)


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
    """Một lần trao **một hộp**, trong một năm.

    Khoá duy nhất là **(khách, năm, số thứ tự)**. Đ-9 bỏ khái niệm "mốc" nên không
    còn khoá theo mốc được nữa; thay bằng ``sequence`` — hộp thứ mấy trong năm. Số
    thứ tự làm hai việc cùng lúc: chặn trao trùng (không đi vòng bằng giao diện nhớ
    hộ), và cho người đọc sổ trả lời được *"đây là hộp thứ mấy, ứng với bậc 2 triệu
    thứ mấy"* mà không phải đếm lại cả danh sách.
    """

    customer_id: UUID
    year: int
    #: Hộp thứ mấy trong năm, đếm từ 1. Phải liên tục — xem :meth:`YearlyLoyalty.grant`.
    sequence: int
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

    @property
    def boxes_granted(self) -> int:
        """Số hộp đã trao trong năm."""
        return len(self.grants)

    def pending_boxes(self) -> int:
        """Số hộp khách đã tích đủ nhưng **chưa nhận** — thứ quầy cần nhìn thấy.

        🔴 **Không bao giờ âm** (Đ-9, Chain chốt 2026-07-30: *không thu hồi*). Khách
        trả hàng sau khi đã nhận quà thì tích luỹ tụt xuống, số hộp được hưởng có thể
        **thấp hơn số đã trao** — khi đó kết quả là 0, không phải số âm. Hộp khẩu trang
        đã cho thì không đòi lại, và cũng không ghi nợ: khách phải mua thêm cho tới bậc
        2 triệu kế tiếp mới sinh ra hộp mới.

        Hệ quả cần biết: sau một lần trả hàng lớn, khách có thể mua thêm một lúc mà
        vẫn chưa có hộp nào — đúng ý *"khoá ở mức đã trao"*, không phải lỗi.
        """
        return max(0, boxes_earned(self.accrued) - self.boxes_granted)

    def grant(self, grant: RewardGrant) -> None:
        """Ghi nhận đã trao một hộp.

        Ba phép kiểm, cả ba đặt ở domain chứ không ở giao diện — đây là chỗ **hàng
        thật rời kho thật**, nên nó phải chặt ở nơi mọi đường đều đi qua:

        1. **Chưa tích đủ bậc kế tiếp thì không trao.**
        2. **Không trao vượt số được hưởng** — chặn cả trường hợp gọi nhiều lần liên
           tiếp khi chỉ còn đúng một hộp.
        3. **Số thứ tự phải liên tục** (``sequence == boxes_granted + 1``). Không có
           phép kiểm này thì hai lượt trao đồng thời cùng ghi ``sequence=3`` và sổ mất
           khả năng trả lời *"đã trao mấy hộp"* — cùng họ với rủi ro cộng trùng
           ``order_id`` mà :meth:`accrue` đã chặn.
        """
        duoc_huong = boxes_earned(self.accrued)
        if duoc_huong == 0:
            raise RewardNotEarnedError(
                f"Chưa đủ bậc {REWARD_STEP:,.0f} đ — mới tích {self.accrued:,.0f} đ"
            )
        if self.boxes_granted >= duoc_huong:
            raise RewardAlreadyGrantedError(
                f"Đã trao {self.boxes_granted} hộp trong năm {self.year}, "
                f"tích luỹ {self.accrued:,.0f} đ chỉ được hưởng {duoc_huong} hộp"
            )
        mong_doi = self.boxes_granted + 1
        if grant.sequence != mong_doi:
            raise RewardAlreadyGrantedError(
                f"Hộp phải trao theo thứ tự liên tục — chờ số {mong_doi}, nhận số {grant.sequence}"
            )
        self.grants.append(grant)
