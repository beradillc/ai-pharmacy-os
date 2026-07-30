"""Catalog aggregates: :class:`Drug` and its sellable units."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pharmacy_os.modules.catalog.domain.exceptions import (
    DuplicateIngredientError,
    DuplicateUnitError,
    InvalidIngredientError,
)


class RxClass(StrEnum):
    """Dispensing class per Vietnamese regulation."""

    OTC = "OTC"  # thuốc không kê đơn
    ETC = "ETC"  # thuốc kê đơn
    CONTROLLED = "CONTROLLED"  # thuốc kiểm soát đặc biệt (TT 20/2017)


@dataclass(slots=True)
class DrugUnit:
    """A saleable/packaging unit and its factor toward the drug's base unit.

    Example: base unit "viên"; a "vỉ" of 10 has ``factor = 10``.
    """

    unit_name: str
    factor: Decimal
    is_sellable: bool = True
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.factor = Decimal(self.factor)
        if self.factor <= 0:
            raise ValueError("Đơn vị quy đổi phải có hệ số > 0")


@dataclass(slots=True)
class ActiveIngredient:
    """Global active-ingredient reference (docs/03 ERD ``active_ingredients``).

    Shared across tenants — like :class:`RxClass` categories, this is reference data,
    not a tenant-owned record: pharmacology facts ("hoạt chất") don't vary per pharmacy.
    Looked up by :attr:`id` from :class:`DrugIngredient`; matched/deduplicated by
    :attr:`name` (case/space-insensitive) at the application layer, not enforced here.
    """

    name: str
    name_en: str | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidIngredientError("Tên hoạt chất không được để trống")


@dataclass(slots=True)
class DrugIngredient:
    """One active ingredient's dosage strength within a drug (docs/03 ``drug_ingredients``).

    A drug carrying more than one ingredient is the normal case, not an edge case —
    combination products (e.g. amoxicillin + acid clavulanic) are common in practice.
    ``amount``/``unit`` is the dosage strength of *this* ingredient in *this* drug (e.g.
    500 mg); it is independent of the drug's own ``base_unit`` (a packaging/dispensing
    unit, e.g. "viên") and of any other ingredient's strength on the same drug.
    """

    ingredient_id: UUID
    amount: Decimal
    unit: str
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.amount = Decimal(self.amount)
        if self.amount <= 0:
            raise InvalidIngredientError("Hàm lượng hoạt chất phải > 0")
        if not self.unit.strip():
            raise InvalidIngredientError("Đơn vị hàm lượng hoạt chất không được để trống")


@dataclass(slots=True)
class Drug:
    """Drug master record (aggregate root)."""

    name: str
    rx_class: RxClass
    base_unit: str
    registration_no: str | None = None
    atc_code: str | None = None
    form: str | None = None
    strength: str | None = None
    barcode: str | None = None
    sale_price: Decimal | None = None
    """Giá bán lẻ trên MỘT đơn vị lẻ (``base_unit``), hoặc ``None`` khi chưa đặt.

    Nullable và sẽ mãi nullable: một nhà thuốc nhập danh mục từ nhà phân phối
    trước, chốt giá sau, và một thuốc chưa có giá phải nhập được chứ không bị
    chặn ở cửa. Nơi bán hàng đọc trường này để **điền sẵn**, không phải để khoá
    — thu ngân vẫn sửa được từng dòng (khuyến mãi, giá lẻ theo khách).

    Không phải giá vốn: giá vốn nằm ở từng lô (``product_batches.cost_price``)
    vì mỗi lần nhập một giá; giá bán là thuộc tính của mặt hàng.
    """
    id: UUID = field(default_factory=uuid4)
    units: list[DrugUnit] = field(default_factory=list)
    ingredients: list[DrugIngredient] = field(default_factory=list)

    def add_unit(self, unit: DrugUnit) -> None:
        if unit.unit_name == self.base_unit or any(
            u.unit_name == unit.unit_name for u in self.units
        ):
            raise DuplicateUnitError(f"Đơn vị '{unit.unit_name}' đã tồn tại cho thuốc này")
        self.units.append(unit)

    def add_ingredient(self, ingredient: DrugIngredient) -> None:
        if any(i.ingredient_id == ingredient.ingredient_id for i in self.ingredients):
            raise DuplicateIngredientError("Hoạt chất này đã được thêm cho thuốc")
        self.ingredients.append(ingredient)

    def replace_ingredients(self, ingredients: list[DrugIngredient]) -> None:
        """Đặt lại TOÀN BỘ danh sách hoạt chất — sửa nhầm, bổ sung thiếu, xoá sai.

        Vì sao thay cả danh sách chứ không thêm/xoá từng cái: ca dùng thật là *sửa một
        hoạt chất nhập sai*, mà "sửa" = xoá cái sai + thêm cái đúng. Làm hai lượt thì tồn
        tại một khoảng thuốc mang danh sách **sai theo cách khác** — và trong khoảng đó
        cảnh báo dị ứng vẫn đang chạy. Một lượt thì không có khoảng đó.

        Danh sách rỗng là **hợp lệ**: băng gạc, khẩu trang, nhiệt kế đúng là không có hoạt
        chất nào. Nhưng nó cũng chính là cách vô hiệu hoá cảnh báo dị ứng cho một thuốc,
        nên tầng ứng dụng phải ghi vết số lượng trước/sau — ở đây không chặn được, vì
        domain không biết thuốc này là thuốc hay vật tư.

        **Toàn-bộ-hoặc-không-gì:** trùng hoạt chất thì `DuplicateIngredientError` và
        `self.ingredients` **giữ nguyên như trước khi gọi**. Áp dụng nửa vời một danh sách
        hoạt chất trên tính năng cảnh báo dị ứng còn tệ hơn từ chối hẳn.
        """
        seen: set[UUID] = set()
        for i in ingredients:
            if i.ingredient_id in seen:
                raise DuplicateIngredientError(
                    f"Hoạt chất {i.ingredient_id} xuất hiện hai lần trong danh sách"
                )
            seen.add(i.ingredient_id)
        self.ingredients = list(ingredients)

    def is_prescription_required(self) -> bool:
        return self.rx_class in (RxClass.ETC, RxClass.CONTROLLED)

    def to_base_quantity(self, quantity: Decimal, unit_name: str) -> Decimal:
        """Convert *quantity* expressed in *unit_name* into base units."""
        if unit_name == self.base_unit:
            return Decimal(quantity)
        for u in self.units:
            if u.unit_name == unit_name:
                return Decimal(quantity) * u.factor
        raise ValueError(f"Không rõ đơn vị '{unit_name}' cho thuốc {self.name}")
