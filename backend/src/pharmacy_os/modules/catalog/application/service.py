"""Catalog use-cases.

The service depends only on ports; concrete repositories and the unit of work
are injected as factories at composition time (see the module ``register``).
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import ConflictError, NotFoundError, ValidationError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.catalog.application.dto import CreateDrugInput, DrugOutput
from pharmacy_os.modules.catalog.domain import Drug, DrugUnit, DuplicateUnitError, RxClass
from pharmacy_os.modules.catalog.domain.ports import DrugRepository

UowFactory = Callable[[], UnitOfWork]
RepoFactory = Callable[[UnitOfWork, RequestContext], DrugRepository]


class CatalogService:
    def __init__(self, uow_factory: UowFactory, repo_factory: RepoFactory) -> None:
        self._uow_factory = uow_factory
        self._repo_factory = repo_factory

    async def create_drug(self, data: CreateDrugInput, ctx: RequestContext) -> DrugOutput:
        require_permission(ctx, "catalog.create")
        drug = Drug(
            name=data.name,
            rx_class=RxClass(data.rx_class),
            base_unit=data.base_unit,
            registration_no=data.registration_no,
            atc_code=data.atc_code,
            form=data.form,
            strength=data.strength,
            barcode=data.barcode,
        )
        try:
            for u in data.units:
                drug.add_unit(
                    DrugUnit(unit_name=u.unit_name, factor=u.factor, is_sellable=u.is_sellable)
                )
        except DuplicateUnitError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            if data.barcode and await repo.by_barcode(data.barcode) is not None:
                raise ConflictError(f"Barcode '{data.barcode}' đã tồn tại")
            await repo.add(drug)
            await uow.commit()
        return DrugOutput.of(drug)

    async def get_drug(self, drug_id: UUID, ctx: RequestContext) -> DrugOutput:
        require_permission(ctx, "catalog.read")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            drug = await repo.get(drug_id)
        if drug is None:
            raise NotFoundError(f"Không tìm thấy thuốc {drug_id}")
        return DrugOutput.of(drug)

    async def list_drugs(
        self, ctx: RequestContext, *, limit: int = 50, offset: int = 0
    ) -> list[DrugOutput]:
        require_permission(ctx, "catalog.read")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            drugs = await repo.list(limit=limit, offset=offset)
        return [DrugOutput.of(d) for d in drugs]
