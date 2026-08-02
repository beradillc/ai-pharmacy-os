"""Uỷ quyền quản trị có thời hạn — domain thuần (Chain chốt 2026-08-03).

Xem `docs/features/uy-quyen-quan-tri/01_DECISIONS.md`.

**Vấn đề nó giải.** Vai *Quản trị hệ thống* hôm nay giữ **56/56 quyền**, trong đó 25 quyền chạm
hồ sơ bệnh nhân — thường trực, không ai cấp, không có hạn. Chain bác phương án cắt quyền, và
bác đúng: một người bảo trì làm việc mù sẽ mở ``psql``, nơi **không có vết kiểm toán nào**. Đích
không phải *ít quyền hơn* mà là **quyền cao nhất phải đắt nhất để dùng**: có người cấp, có lý
do, có hạn, và có báo cáo lại.

🔴 **Vì sao lưu ẢNH CHỤP quyền vào chính bản ghi uỷ quyền**, thay vì suy lại từ vai người cấp
mỗi lần dùng: vai trò đổi được sau khi uỷ quyền đã cấp. Nếu suy lại lúc dùng thì một lần nâng
quyền cho chủ chuỗi sẽ **âm thầm nới rộng mọi uỷ quyền đang mở** — người cấp không hề biết mình
vừa cho thêm cái gì. Ảnh chụp làm phạm vi đúng bằng thứ được nhìn thấy lúc bấm nút.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

THOI_HAN = timedelta(hours=24)
"""Chain chốt: **24 giờ mỗi lần xác nhận**, cố định.

Không cho người cấp tự chọn thời hạn — một ô nhập số giờ là một ô người ta sẽ điền số lớn
nhất được phép, và khi ấy "có hạn" chỉ còn là hình thức. Cần dài hơn thì **xác nhận lại**, và
lần xác nhận thứ hai là một dòng audit thứ hai."""

LY_DO_TOI_THIEU = 10
"""Lý do phải là một câu, không phải một ký tự.

Ngưỡng thấp có chủ đích: mục tiêu là chặn ``"."`` và ``"x"``, không phải ép người đang xử lý
sự cố viết văn. Một trường bắt buộc quá khắt khe sẽ được điền bằng ``"aaaaaaaaaa"`` — tệ hơn,
vì nó trông như một lý do thật."""

KHONG_UY_QUYEN_DUOC = frozenset({"compliance.ledger.sign"})
"""🔴 Quyền **không bao giờ** đi qua uỷ quyền, dù người cấp có nó.

``compliance.ledger.sign`` là chữ ký sổ thuốc kiểm soát đặc biệt — **lời khai của một dược sĩ
có Chứng chỉ hành nghề** trước cơ quan quản lý, không phải một quyền phần mềm. Chủ chuỗi nhận
được trách nhiệm dân sự/quản trị, nhưng **tư cách chuyên môn không chuyển sang người khác bằng
một thao tác trong phần mềm**. Một chữ ký sai người trong sổ pháp lý là thứ không sửa lại được
sau khi đã nộp.

🔴 **Danh sách này phải tồn tại tường minh** — không suy ra được từ ràng buộc "không cấp thứ
mình không có". Đã kiểm bằng lệnh: vai ``chain_pharmacist`` **CÓ** ``compliance.ledger.sign``
(đúng như phải thế — chủ chuỗi là người ký sổ hợp pháp), nên ràng buộc kia **không** chặn được
đường chuyển quyền ký sang một tài khoản kỹ thuật.

Là **hằng số trong domain**, không phải cấu hình: một quyền chỉ ra khỏi đây bằng cách sửa mã và
qua cổng, không bằng một dòng ``.env`` gõ vội lúc 2 giờ sáng đang xử lý sự cố."""


class UyQuyenKhongHopLe(ValueError):
    """Yêu cầu uỷ quyền không thoả luật domain."""


@dataclass(slots=True)
class UyQuyenQuanTri:
    """Một lần chủ chuỗi mở quyền nghiệp vụ cho một tài khoản, trong 24 giờ.

    ``quyen`` là **ảnh chụp** tại thời điểm cấp — xem ghi chú đầu tệp.
    """

    tenant_id: UUID
    nguoi_nhan_id: UUID
    nguoi_cap_id: UUID
    ly_do: str
    quyen: frozenset[str]
    cap_luc: datetime
    het_han_luc: datetime
    thu_hoi_luc: datetime | None = None
    id: UUID = field(default_factory=uuid4)

    def con_hieu_luc(self, bay_gio: datetime) -> bool:
        """Còn hiệu lực = chưa thu hồi **và** chưa tới hạn.

        Hết hạn là một **phép so thời gian**, không phải một tác vụ nền phải chạy đúng giờ.
        Máy mất điện ba ngày rồi bật lại thì uỷ quyền cũ vẫn hết hạn đúng lúc nó phải hết —
        không có job nào cần "đuổi kịp". Thứ phải nhớ chạy là thứ sẽ quên.
        """
        if self.thu_hoi_luc is not None:
            return False
        return bay_gio < self.het_han_luc


def tao_uy_quyen(
    *,
    tenant_id: UUID,
    nguoi_nhan_id: UUID,
    nguoi_cap_id: UUID,
    ly_do: str,
    quyen_nguoi_cap: frozenset[str],
    bay_gio: datetime | None = None,
) -> UyQuyenQuanTri:
    """Dựng một uỷ quyền hợp lệ, hoặc ném :class:`UyQuyenKhongHopLe`.

    Bốn luật, theo thứ tự nghiêm trọng giảm dần:

    1. **Không tự uỷ quyền cho chính mình.** Một người vừa cấp vừa nhận thì không còn ai là
       người chịu trách nhiệm — mà "chủ chuỗi chịu trách nhiệm" là điều kiện Chain đặt ra.
       *(Ngoại lệ vận hành: ở quầy một người, chủ chuỗi và quản trị hệ thống là hai **tài
       khoản** khác nhau của cùng một người. Luật này ép đúng điều đó — hai tài khoản, hai
       vết.)*
    2. **Không cấp quá thứ mình có.** Uỷ quyền không bao giờ rộng hơn người ký nó.
    3. **Không cấp thứ nằm trong :data:`KHONG_UY_QUYEN_DUOC`**, dù người cấp có.
    4. **Phải có lý do.**
    """
    bay_gio = bay_gio or datetime.now(UTC)

    if nguoi_cap_id == nguoi_nhan_id:
        raise UyQuyenKhongHopLe(
            "Không tự uỷ quyền cho chính mình: phải có một người chịu trách nhiệm khác người "
            "sử dụng quyền."
        )
    if len(ly_do.strip()) < LY_DO_TOI_THIEU:
        raise UyQuyenKhongHopLe(
            f"Lý do uỷ quyền phải có ít nhất {LY_DO_TOI_THIEU} ký tự — nó đi vào sổ kiểm toán "
            "và là thứ người ta đọc lại khi rà."
        )

    xin = frozenset(quyen_nguoi_cap)
    vuot = xin & KHONG_UY_QUYEN_DUOC
    if vuot:
        raise UyQuyenKhongHopLe(
            f"Không uỷ quyền được: {', '.join(sorted(vuot))}. Đây là hành vi pháp lý gắn với "
            "Chứng chỉ hành nghề dược của một con người, không phải một quyền phần mềm."
        )

    if not xin:
        raise UyQuyenKhongHopLe("Không có quyền nào để uỷ quyền.")

    return UyQuyenQuanTri(
        tenant_id=tenant_id,
        nguoi_nhan_id=nguoi_nhan_id,
        nguoi_cap_id=nguoi_cap_id,
        ly_do=ly_do.strip(),
        quyen=xin,
        cap_luc=bay_gio,
        het_han_luc=bay_gio + THOI_HAN,
    )


def loc_quyen_uy_quyen_duoc(quyen_nguoi_cap: frozenset[str]) -> frozenset[str]:
    """Phần uỷ quyền được của một bộ quyền — dùng để **hiện trước cho người cấp xem**.

    Tách khỏi :func:`tao_uy_quyen` có chủ đích: hàm kia **ném lỗi** khi gặp quyền cấm, hàm này
    **lọc im lặng**. Hai hành vi cho hai chỗ dùng khác nhau — màn hình cần biết *"cấp được cái
    gì"*, còn lúc ghi thì một quyền cấm lọt vào phải là **lỗi ồn ào**, không phải một thứ bị bỏ
    qua lặng lẽ.
    """
    return frozenset(quyen_nguoi_cap) - KHONG_UY_QUYEN_DUOC
