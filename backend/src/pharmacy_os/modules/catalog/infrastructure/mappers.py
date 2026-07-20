"""Mapping between catalog ORM rows and domain entities."""

from __future__ import annotations

from uuid import UUID

from pharmacy_os.modules.catalog.domain import Drug, DrugUnit, RxClass
from pharmacy_os.modules.catalog.infrastructure.models import DrugORM, DrugUnitORM


def to_domain(row: DrugORM) -> Drug:
    drug = Drug(
        id=row.id,
        name=row.name,
        rx_class=RxClass(row.rx_class),
        base_unit=row.base_unit,
        registration_no=row.registration_no,
        atc_code=row.atc_code,
        form=row.form,
        strength=row.strength,
        barcode=row.barcode,
    )
    drug.units = [
        DrugUnit(id=u.id, unit_name=u.unit_name, factor=u.factor, is_sellable=u.is_sellable)
        for u in row.units
    ]
    return drug


def to_orm(drug: Drug, tenant_id: UUID) -> DrugORM:
    return DrugORM(
        id=drug.id,
        tenant_id=tenant_id,
        name=drug.name,
        rx_class=drug.rx_class.value,
        base_unit=drug.base_unit,
        registration_no=drug.registration_no,
        atc_code=drug.atc_code,
        form=drug.form,
        strength=drug.strength,
        barcode=drug.barcode,
        units=[
            DrugUnitORM(
                id=u.id,
                drug_id=drug.id,
                unit_name=u.unit_name,
                factor=u.factor,
                is_sellable=u.is_sellable,
            )
            for u in drug.units
        ],
    )
