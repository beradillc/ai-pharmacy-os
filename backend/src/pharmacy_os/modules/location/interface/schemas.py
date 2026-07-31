"""Pydantic schema cho sơ đồ kho."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from pharmacy_os.modules.location.application.dto import (
    CreateLocationInput,
    LocationOutput,
    UpdateLocationInput,
)
from pharmacy_os.modules.location.domain import MAX_CODE_LENGTH


class CreateLocationRequest(BaseModel):
    """Tạo một vị trí.

    ``kind`` là chuỗi chứ không phải enum của Pydantic để lỗi trả về là **422 có thông
    điệp đọc được** từ tầng ứng dụng (*"Tầng vị trí không hợp lệ: KE"*) thay vì một lỗi
    lược đồ liệt kê bốn giá trị hợp lệ mà không nói cái nào sai.
    """

    kind: str = Field(max_length=16)
    code: str = Field(min_length=1, max_length=MAX_CODE_LENGTH)
    name: str | None = Field(default=None, max_length=255)
    #: ``null`` = tạo một KHO gốc.
    parent_id: UUID | None = None
    pick_order: int = Field(default=0, ge=0)

    def to_input(self) -> CreateLocationInput:
        return CreateLocationInput(
            kind=self.kind,
            code=self.code,
            name=self.name,
            parent_id=self.parent_id,
            pick_order=self.pick_order,
        )


class UpdateLocationRequest(BaseModel):
    """Sửa vị trí. **Không có `code`** — mã bất biến sau khi tạo, xem ``Location``.

    Cả ba trường đều ``None`` mặc định, nghĩa là *"không đổi"*. Khác hẳn ``name=null``
    nghĩa là *"xoá tên hiển thị"* — nên ``name`` không phân biệt được hai ý đó và đó là
    đánh đổi đã chấp nhận: xoá tên là thao tác hiếm, đổi tên thì không.
    """

    name: str | None = Field(default=None, max_length=255)
    pick_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

    def to_input(self) -> UpdateLocationInput:
        return UpdateLocationInput(
            name=self.name, pick_order=self.pick_order, is_active=self.is_active
        )


class LocationResponse(BaseModel):
    id: UUID
    parent_id: UUID | None
    kind: str
    code: str
    #: Đường dẫn đầy đủ (``KHO1/A/A01/03``) — thứ hiện cho người dùng, không phải UUID.
    path: str
    name: str | None
    is_active: bool
    pick_order: int

    @classmethod
    def of(cls, out: LocationOutput) -> LocationResponse:
        return cls(
            id=out.id,
            parent_id=out.parent_id,
            kind=out.kind,
            code=out.code,
            path=out.path,
            name=out.name,
            is_active=out.is_active,
            pick_order=out.pick_order,
        )
