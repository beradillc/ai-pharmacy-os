"""Pydantic request/response schemas for catalog."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from pharmacy_os.modules.catalog.application.dto import (
    ActiveIngredientOutput,
    CreateDrugInput,
    CreateIngredientInput,
    DrugIngredientInput,
    DrugOutput,
    DrugUnitInput,
    PriceHistoryOutput,
)
from pharmacy_os.modules.catalog.domain import RxClass


class CreateIngredientRequest(BaseModel):
    # max_length khớp đúng độ rộng cột — không chặn ở đây thì Postgres ném
    # StringDataRightTruncationError và client nhận 500 thay vì 422 (PROJECT_STATE §7aq).
    name: str = Field(max_length=255)
    name_en: str | None = Field(default=None, max_length=255)

    def to_input(self) -> CreateIngredientInput:
        return CreateIngredientInput(name=self.name, name_en=self.name_en)


class ActiveIngredientResponse(BaseModel):
    id: UUID
    name: str
    name_en: str | None

    @classmethod
    def of(cls, out: ActiveIngredientOutput) -> ActiveIngredientResponse:
        return cls(id=out.id, name=out.name, name_en=out.name_en)


class DrugUnitSchema(BaseModel):
    unit_name: str = Field(max_length=32)
    factor: Decimal = Field(gt=0)
    is_sellable: bool = True


class DrugIngredientSchema(BaseModel):
    ingredient_id: UUID
    amount: Decimal = Field(gt=0)
    unit: str = Field(max_length=32)


class ReplaceDrugIngredientsRequest(BaseModel):
    """Danh sách hoạt chất MỚI của thuốc — thay toàn bộ, không phải thêm vào.

    Danh sách rỗng là hợp lệ và **có nghĩa**: nó xoá hết hoạt chất của thuốc. Đó là câu
    trả lời đúng cho vật tư (băng gạc, khẩu trang, nhiệt kế) và cũng chính là cách vô hiệu
    hoá cảnh báo dị ứng cho một mã hàng — nên nó không mặc định được, người gọi phải gửi
    trường ``ingredients`` một cách tường minh. Nhầm lẫn ở đây im lặng và nguy hiểm, vì
    body rỗng ``{}`` mà lỡ có mặc định sẽ xoá sạch mà trông như một lượt gọi vô hại.
    """

    ingredients: list[DrugIngredientSchema]

    def to_input(self) -> list[DrugIngredientInput]:
        return [
            DrugIngredientInput(ingredient_id=i.ingredient_id, amount=i.amount, unit=i.unit)
            for i in self.ingredients
        ]


class CreateDrugRequest(BaseModel):
    name: str = Field(max_length=255)
    rx_class: RxClass
    base_unit: str = Field(max_length=32)
    registration_no: str | None = Field(default=None, max_length=64)
    atc_code: str | None = Field(default=None, max_length=16)
    form: str | None = Field(default=None, max_length=64)
    strength: str | None = Field(default=None, max_length=64)
    barcode: str | None = Field(default=None, max_length=64)
    #: Giá bán lẻ một đơn vị lẻ. ``ge=0`` chứ không ``gt=0``: hàng khuyến mãi giá 0
    #: là chuyện có thật, còn giá âm thì không.
    sale_price: Decimal | None = Field(default=None, ge=0)
    units: list[DrugUnitSchema] = Field(default_factory=list)
    ingredients: list[DrugIngredientSchema] = Field(default_factory=list)

    def to_input(self) -> CreateDrugInput:
        return CreateDrugInput(
            name=self.name,
            rx_class=self.rx_class,
            base_unit=self.base_unit,
            registration_no=self.registration_no,
            atc_code=self.atc_code,
            form=self.form,
            strength=self.strength,
            barcode=self.barcode,
            sale_price=self.sale_price,
            units=[
                DrugUnitInput(unit_name=u.unit_name, factor=u.factor, is_sellable=u.is_sellable)
                for u in self.units
            ],
            ingredients=[
                DrugIngredientInput(ingredient_id=i.ingredient_id, amount=i.amount, unit=i.unit)
                for i in self.ingredients
            ],
        )


class DrugUnitResponse(BaseModel):
    unit_name: str
    factor: Decimal
    is_sellable: bool


class DrugIngredientResponse(BaseModel):
    ingredient_id: UUID
    amount: Decimal
    unit: str


class DrugResponse(BaseModel):
    id: UUID
    name: str
    rx_class: str
    base_unit: str
    registration_no: str | None
    atc_code: str | None
    form: str | None
    strength: str | None
    barcode: str | None
    sale_price: Decimal | None
    prescription_required: bool
    units: list[DrugUnitResponse]
    ingredients: list[DrugIngredientResponse]

    @classmethod
    def of(cls, out: DrugOutput) -> DrugResponse:
        return cls(
            id=out.id,
            name=out.name,
            rx_class=out.rx_class,
            base_unit=out.base_unit,
            registration_no=out.registration_no,
            atc_code=out.atc_code,
            form=out.form,
            strength=out.strength,
            barcode=out.barcode,
            sale_price=out.sale_price,
            prescription_required=out.prescription_required,
            units=[
                DrugUnitResponse(unit_name=u.unit_name, factor=u.factor, is_sellable=u.is_sellable)
                for u in out.units
            ],
            ingredients=[
                DrugIngredientResponse(ingredient_id=i.ingredient_id, amount=i.amount, unit=i.unit)
                for i in out.ingredients
            ],
        )


class SetDrugPriceRequest(BaseModel):
    """Đặt lại giá bán niêm yết của một thuốc.

    ``ge=0`` chứ không ``gt=0``: hàng tặng/hàng mẫu giá 0 là chuyện có thật, giá âm thì
    không — cùng lý do đã ghi ở ``CreateDrugRequest.sale_price``.

    ``reason`` không bắt buộc **ở tầng lược đồ** dù nghiệp vụ đòi khi đổi giá đã có: quy
    tắc *"có giá rồi thì phải ghi lý do"* phụ thuộc vào trạng thái **của thuốc trong CSDL**,
    thứ mà một lược đồ yêu cầu không nhìn thấy. Bắt buộc ở đây sẽ chặn luôn lần đặt giá
    đầu tiên. Cưỡng chế thật nằm ở ``CatalogService.set_drug_price`` (422).
    """

    new_price: Decimal = Field(ge=0)
    reason: str | None = Field(default=None, max_length=255)


class PriceHistoryResponse(BaseModel):
    """Một dòng lịch sử giá. ``old_price is None`` = lần ĐẦU đặt giá, không phải đổi giá."""

    id: UUID
    old_price: Decimal | None
    new_price: Decimal
    reason: str | None
    changed_by: UUID | None
    changed_at: datetime

    @classmethod
    def of(cls, out: PriceHistoryOutput) -> PriceHistoryResponse:
        return cls(
            id=out.id,
            old_price=out.old_price,
            new_price=out.new_price,
            reason=out.reason,
            changed_by=out.changed_by,
            changed_at=out.changed_at,
        )
