"""Sơ đồ kho: cây vị trí lưu trữ. Thuần, không framework.

🔴 Vì sao đây là module RIÊNG, không nhét vào ``inventory``: sơ đồ kho là **dữ liệu cấu
hình của cơ sở** — đặt một lần, sửa vài lần một năm. Chuyển động hàng là **dòng sự kiện**
— hàng nghìn dòng mỗi tháng. Hai vòng đời đó không có lý do gì phải chung một module, và
nhét chung sẽ làm contract ``import-linter`` của ``inventory`` mất nghĩa.

Module này **không đụng một dòng nào** của ``inventory``, ``catalog`` hay ``sales``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID, uuid4

from pharmacy_os.modules.location.domain.exceptions import (
    InvalidLocationCodeError,
    InvalidLocationNestingError,
    LocationHasChildrenError,
)

#: Ký tự ngăn cách trong đường dẫn hiển thị (``A / A01 / 03``). Cũng là ký tự **cấm** xuất
#: hiện trong mã, nếu không đường dẫn sẽ không tách ngược lại được.
PATH_SEPARATOR = "/"

MAX_CODE_LENGTH = 32


class LocationKind(StrEnum):
    """Tầng trong sơ đồ kho.

    🔴 Đây là **từ vựng tầng**, KHÔNG phải mã vị trí. Yêu cầu *"không hard-code A/B/C"* nói
    về **mã** — và mã do nhà thuốc tự đặt, hệ thống không biết trước chữ nào. Từ vựng tầng
    thì phải đóng: nếu cho tự do đặt tên tầng, không có cách nào biết Kệ nằm trong Khu hay
    ngược lại, và mọi phép sắp xếp đường đi lấy hàng sẽ mất căn cứ.

    Thứ tự khai báo **là** thứ bậc — xem :meth:`can_contain`.
    """

    WAREHOUSE = "WAREHOUSE"
    ZONE = "ZONE"
    SHELF = "SHELF"
    BIN = "BIN"

    @property
    def depth(self) -> int:
        return _KIND_ORDER[self]

    def can_contain(self, child: LocationKind) -> bool:
        """Tầng này chứa được *child* không? Bỏ tầng thì được, đảo tầng thì không.

        Nhà thuốc nhỏ chỉ có Kho → Kệ là chuyện thường; bắt họ tạo Khu rỗng cho đủ tầng là
        bắt họ nhập dữ liệu giả.
        """
        return child.depth > self.depth


_KIND_ORDER: dict[LocationKind, int] = {
    LocationKind.WAREHOUSE: 0,
    LocationKind.ZONE: 1,
    LocationKind.SHELF: 2,
    LocationKind.BIN: 3,
}


def normalize_code(code: str) -> str:
    """Chuẩn hoá mã vị trí: bỏ khoảng trắng thừa, viết HOA.

    Viết hoa vì mã vị trí được **đọc từ nhãn dán trên kệ và gõ lại bằng tay** — ``a01`` và
    ``A01`` là cùng một chỗ với người đứng kho, nên chúng phải là cùng một chỗ với hệ thống.
    Không chuẩn hoá sẽ đẻ ra hai vị trí trông giống hệt nhau trên màn hình.
    """
    ma = code.strip().upper()
    if not ma:
        raise InvalidLocationCodeError("Mã vị trí không được để trống")
    if len(ma) > MAX_CODE_LENGTH:
        raise InvalidLocationCodeError(f"Mã vị trí tối đa {MAX_CODE_LENGTH} ký tự: {ma!r}")
    if PATH_SEPARATOR in ma:
        raise InvalidLocationCodeError(
            f"Mã vị trí không được chứa {PATH_SEPARATOR!r} — đó là ký tự ngăn cách đường dẫn"
        )
    return ma


@dataclass(slots=True)
class Location:
    """Một nút trong sơ đồ kho — Kho, Khu, Kệ hoặc Ô.

    ``path`` là **đường dẫn vật chất hoá** (``A/A01/03``): giữ sẵn để trả lời *"liệt kê mọi
    thứ nằm dưới khu A"* bằng một phép so tiền tố thay vì đệ quy, và để hiện cho người dùng
    một chuỗi đọc được mà không phải nạp cả cây.

    Đánh đổi đã cân: đường dẫn là dữ liệu **thừa** (suy ra được từ cha), nên nó có thể lệch.
    Đổi lại, ``code`` **bất biến sau khi tạo** — sửa mã sẽ buộc phải viết lại đường dẫn của
    cả cây con, đúng loại thao tác hay hỏng nửa chừng. Đổi tên hiển thị (``name``) thì thoải
    mái vì nó không nằm trong đường dẫn.
    """

    tenant_id: UUID
    branch_id: UUID
    kind: LocationKind
    code: str
    path: str
    name: str | None = None
    parent_id: UUID | None = None
    is_active: bool = True
    #: Thứ tự đi lấy hàng trong cùng một cha. Nhỏ hơn = đi tới trước.
    #:
    #: Có ngay từ đầu chứ không đợi Phase 4: quãng đường trong kho **không** suy ra được từ
    #: mã. Kệ A01 và A02 có thể đối lưng nhau qua một lối đi, và chỉ người xếp kho biết.
    #: Thiếu trường này thì Pick List chỉ còn cách sắp theo bảng chữ cái — một phỏng đoán
    #: trông như tối ưu.
    pick_order: int = 0
    id: UUID = field(default_factory=uuid4)

    @classmethod
    def create_root(
        cls,
        *,
        tenant_id: UUID,
        branch_id: UUID,
        code: str,
        name: str | None = None,
        pick_order: int = 0,
    ) -> Location:
        """Tạo một KHO (nút gốc). Kho luôn là gốc — không có gì chứa được một kho."""
        ma = normalize_code(code)
        return cls(
            tenant_id=tenant_id,
            branch_id=branch_id,
            kind=LocationKind.WAREHOUSE,
            code=ma,
            path=ma,
            name=name,
            parent_id=None,
            pick_order=pick_order,
        )

    def create_child(
        self,
        *,
        kind: LocationKind,
        code: str,
        name: str | None = None,
        pick_order: int = 0,
    ) -> Location:
        """Tạo một vị trí con dưới nút này.

        Kiểm tra trùng mã giữa các anh em **không** làm ở đây: aggregate này chỉ giữ chính
        nó, không giữ danh sách con. Tầng ứng dụng hỏi kho dữ liệu rồi ném
        :class:`DuplicateLocationCodeError`. Ràng buộc thật nằm ở chỉ mục duy nhất trong CSDL
        — mã, không phải lời hứa.
        """
        if not self.kind.can_contain(kind):
            raise InvalidLocationNestingError(
                f"Không đặt được {kind.value} bên trong {self.kind.value}"
            )
        if not self.is_active:
            raise InvalidLocationNestingError(
                f"Vị trí {self.path} đã ngừng hoạt động — không thêm chỗ mới bên dưới"
            )
        ma = normalize_code(code)
        return Location(
            tenant_id=self.tenant_id,
            branch_id=self.branch_id,
            kind=kind,
            code=ma,
            path=f"{self.path}{PATH_SEPARATOR}{ma}",
            name=name,
            parent_id=self.id,
            pick_order=pick_order,
        )

    def rename(self, name: str | None) -> None:
        """Đổi **tên hiển thị**. Mã và đường dẫn không đổi — xem docstring của lớp."""
        self.name = name.strip() if name else None

    def set_pick_order(self, pick_order: int) -> None:
        self.pick_order = pick_order

    def deactivate(self, *, active_children: int) -> None:
        """Ngừng hoạt động. Bên gọi phải đếm số con đang hoạt động và truyền vào.

        Nhận con số thay vì tự đếm vì aggregate không giữ danh sách con — và bắt bên gọi
        truyền vào khiến việc **quên kiểm** trở thành lỗi biên dịch chứ không phải một
        khoảng trống im lặng.
        """
        if active_children > 0:
            raise LocationHasChildrenError(
                f"Vị trí {self.path} còn {active_children} chỗ con đang hoạt động"
            )
        self.is_active = False

    def reactivate(self) -> None:
        self.is_active = True

    def is_descendant_of(self, other: Location) -> bool:
        return self.path.startswith(f"{other.path}{PATH_SEPARATOR}")
