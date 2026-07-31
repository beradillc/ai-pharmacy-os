"""Kiểm kê theo ô — đếm tay, so với sổ, chênh thì **chờ duyệt** (BERAS V2 Phase 11).

🔴 Vì sao KHÔNG dùng lại :class:`StockReconciliationNeeded`: bản ghi đó mang ``grn_id``
**bắt buộc** — nó là cờ cho *một phiếu nhập vào không trọn vẹn*, không phải một bản ghi sai
lệch tổng quát. Cho ``grn_id`` thành nullable là sửa một thực thể đã có test, tức đúng thứ
kỷ luật #17 bảo phải hỏi Chain. Thêm mới rẻ hơn và không đụng gì đang chạy.

🔴 Vì sao chênh lệch phải **chờ duyệt** chứ không tự áp vào tồn kho:

    Con số đếm được là một *lời khai*, không phải một *sự thật*.

Đếm sót một hộp nằm khuất sau lô khác thì hệ thống sẽ ghi nhận mất hàng — và một khi đã ghi
thành chuyển động ``ADJUST`` thì nó nằm trong sổ vĩnh viễn, kèm giá vốn. Nhà thuốc đông
khách kiểm kê giữa ca càng dễ lệch. Chi phí của một bước duyệt là vài giây; chi phí của một
lần tự áp sai là một dòng mất mát giả trong báo cáo mà không ai truy được nữa.

Ba trạng thái, một chiều, không quay lui:

    ĐANG ĐẾM ──submit──> CHỜ DUYỆT ──duyệt──> ĐÃ DUYỆT (sinh chuyển động ADJUST)
                                    └─từ chối─> TỪ CHỐI (không đụng tồn kho)

Không có đường từ CHỜ DUYỆT về ĐANG ĐẾM: sửa một phiên đã nộp thì con số "hệ thống ghi bao
nhiêu tại lúc nộp" mất nghĩa. Đếm lại là **một phiên mới** — rẻ, và để lại vết cả hai lần.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4


class CountStatus(StrEnum):
    """Trạng thái phiên kiểm kê. Đóng — thêm giá trị là đổi hợp đồng, không phải thêm cờ."""

    DANG_DEM = "DANG_DEM"
    CHO_DUYET = "CHO_DUYET"
    DA_DUYET = "DA_DUYET"
    TU_CHOI = "TU_CHOI"


class CountError(Exception):
    """Vi phạm quy tắc kiểm kê. Tầng interface dịch sang 409."""


@dataclass(slots=True)
class CountLine:
    """Một dòng đếm: **một lô** trong ô đang kiểm.

    ``system_qty`` được chốt lúc **nộp**, không phải lúc đếm — xem :meth:`StockCount.submit`.
    Để ``None`` khi phiên còn đang đếm là cố ý: một con số chưa chốt phải *nhìn ra được* là
    chưa chốt, không được giả vờ bằng 0.
    """

    batch_id: UUID
    counted_qty: Decimal
    system_qty: Decimal | None = None
    id: UUID = field(default_factory=uuid4)

    @property
    def lech(self) -> Decimal | None:
        """Đếm được trừ đi sổ ghi. Dương = thừa, âm = thiếu, ``None`` = chưa chốt."""
        if self.system_qty is None:
            return None
        return self.counted_qty - self.system_qty


@dataclass(slots=True)
class StockCount:
    """Một phiên kiểm kê **một vị trí**.

    Phạm vi là một vị trí chứ không phải cả kho, vì đó là đơn vị người ta thật sự đếm được
    trong một lượt đứng dậy. Kiểm cả kho = nhiều phiên, và mỗi phiên duyệt độc lập — hỏng
    một ô không chặn chín ô kia.
    """

    tenant_id: UUID
    branch_id: UUID
    location_id: UUID
    counted_by: UUID
    status: CountStatus = CountStatus.DANG_DEM
    lines: list[CountLine] = field(default_factory=list)
    decided_by: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    submitted_at: datetime | None = None
    decided_at: datetime | None = None

    def dem(self, batch_id: UUID, counted_qty: Decimal) -> None:
        """Ghi số đếm được của một lô. Đếm lại cùng lô thì **đè**, không cộng dồn.

        Đè chứ không cộng: người đếm lại một lô là người vừa phát hiện mình đếm sai, không
        phải người tìm thấy thêm hàng. Cộng dồn ở đây sẽ biến một lần sửa lỗi thành một lần
        khai khống — và không có cách nào nhìn ra từ kết quả.
        """
        if self.status is not CountStatus.DANG_DEM:
            raise CountError("Phiên đã nộp, không sửa được nữa. Muốn đếm lại thì mở phiên mới.")
        if counted_qty < 0:
            raise CountError("Số đếm được không thể âm")
        for dong in self.lines:
            if dong.batch_id == batch_id:
                dong.counted_qty = counted_qty
                return
        self.lines.append(CountLine(batch_id=batch_id, counted_qty=counted_qty))

    def submit(self, *, so_ghi: dict[UUID, Decimal], now: datetime | None = None) -> None:
        """Nộp phiên: **chốt** số sổ đang ghi tại đúng thời điểm này.

        ``so_ghi`` do tầng ứng dụng đọc từ ``stock_at_location`` và truyền vào — domain
        không đi đọc CSDL. Lô nào không có trong ``so_ghi`` nghĩa là sổ ghi **0** ở ô này:
        người đếm tìm thấy hàng mà hệ thống không biết, một phát hiện hợp lệ và thường gặp
        (hàng bị xếp nhầm ô).

        🔴 Chốt lúc nộp chứ không lúc duyệt. Giữa nộp và duyệt có thể có bán hàng — nếu chốt
        lúc duyệt thì chênh lệch sẽ nuốt luôn số đã bán trong khoảng đó, và người duyệt nhìn
        vào một con số không tương ứng với bất kỳ thời điểm nào có thật.
        """
        if self.status is not CountStatus.DANG_DEM:
            raise CountError("Phiên này đã nộp rồi")
        if not self.lines:
            raise CountError("Phiên chưa có dòng nào — đếm ít nhất một lô rồi hãy nộp")
        for dong in self.lines:
            dong.system_qty = so_ghi.get(dong.batch_id, Decimal("0"))
        self.status = CountStatus.CHO_DUYET
        self.submitted_at = now or datetime.now(UTC)

    @property
    def dong_lech(self) -> list[CountLine]:
        """Chỉ những dòng thật sự chênh. Dòng khớp không sinh chuyển động nào."""
        return [d for d in self.lines if d.lech is not None and d.lech != 0]

    def approve(self, *, by: UUID, now: datetime | None = None) -> list[CountLine]:
        """Duyệt. Trả về **đúng những dòng chênh** để tầng ứng dụng ghi ``ADJUST``.

        Domain không tự ghi chuyển động — nó chỉ nói *cái gì phải đổi*. Ai ghi, ghi vào đâu,
        trong giao dịch nào là việc của tầng ngoài.

        Không chặn người đếm tự duyệt phiếu của mình. Nhà thuốc nhỏ chỉ có một người, chặn
        thì tính năng vô dụng với đúng nhóm khách hàng đông nhất. Thay vào đó lưu **cả hai
        tên**, để khi trùng nhau thì *nhìn ra được* — cùng cách làm với cột "Người chốt đơn"
        ở màn Lưu trữ: làm cho thấy được thay vì cấm.
        """
        if self.status is not CountStatus.CHO_DUYET:
            raise CountError(f"Chỉ duyệt được phiên đang chờ duyệt (phiên này: {self.status})")
        self.status = CountStatus.DA_DUYET
        self.decided_by = by
        self.decided_at = now or datetime.now(UTC)
        return self.dong_lech

    def reject(self, *, by: UUID, now: datetime | None = None) -> None:
        """Từ chối. **Không** đụng tới tồn kho — phiên ở lại trong sổ như một vết đã đếm."""
        if self.status is not CountStatus.CHO_DUYET:
            raise CountError(f"Chỉ từ chối được phiên đang chờ duyệt (phiên này: {self.status})")
        self.status = CountStatus.TU_CHOI
        self.decided_by = by
        self.decided_at = now or datetime.now(UTC)
