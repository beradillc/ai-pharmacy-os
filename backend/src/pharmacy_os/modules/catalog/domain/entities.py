"""Catalog aggregates: :class:`Drug` and its sellable units."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pharmacy_os.modules.catalog.domain.exceptions import DuplicateUnitError


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
    id: UUID = field(default_factory=uuid4)
    units: list[DrugUnit] = field(default_factory=list)

    def add_unit(self, unit: DrugUnit) -> None:
        if unit.unit_name == self.base_unit or any(
            u.unit_name == unit.unit_name for u in self.units
        ):
            raise DuplicateUnitError(f"Đơn vị '{unit.unit_name}' đã tồn tại cho thuốc này")
        self.units.append(unit)

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
