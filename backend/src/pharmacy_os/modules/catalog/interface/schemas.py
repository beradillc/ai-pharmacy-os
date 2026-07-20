"""Pydantic request/response schemas for catalog."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from pharmacy_os.modules.catalog.application.dto import (
    CreateDrugInput,
    DrugOutput,
    DrugUnitInput,
)
from pharmacy_os.modules.catalog.domain import RxClass


class DrugUnitSchema(BaseModel):
    unit_name: str
    factor: Decimal = Field(gt=0)
    is_sellable: bool = True


class CreateDrugRequest(BaseModel):
    name: str
    rx_class: RxClass
    base_unit: str
    registration_no: str | None = None
    atc_code: str | None = None
    form: str | None = None
    strength: str | None = None
    barcode: str | None = None
    units: list[DrugUnitSchema] = Field(default_factory=list)

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
            units=[
                DrugUnitInput(unit_name=u.unit_name, factor=u.factor, is_sellable=u.is_sellable)
                for u in self.units
            ],
        )


class DrugUnitResponse(BaseModel):
    unit_name: str
    factor: Decimal
    is_sellable: bool


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
    prescription_required: bool
    units: list[DrugUnitResponse]

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
            prescription_required=out.prescription_required,
            units=[
                DrugUnitResponse(unit_name=u.unit_name, factor=u.factor, is_sellable=u.is_sellable)
                for u in out.units
            ],
        )
