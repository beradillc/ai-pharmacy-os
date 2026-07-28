"""Catalog use-cases.

The service depends only on ports; concrete repositories and the unit of work
are injected as factories at composition time (see the module ``register``).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from uuid import UUID

from pharmacy_os.core.audit import AuditAction, AuditEntry, AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import ConflictError, NotFoundError, ValidationError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.catalog.application.dto import (
    ActiveIngredientOutput,
    CreateDrugInput,
    CreateIngredientInput,
    DrugIngredientRef,
    DrugOutput,
)
from pharmacy_os.modules.catalog.domain import (
    ActiveIngredient,
    Drug,
    DrugIngredient,
    DrugUnit,
    DuplicateIngredientError,
    DuplicateUnitError,
    InvalidIngredientError,
    RxClass,
)
from pharmacy_os.modules.catalog.domain.ports import ActiveIngredientRepository, DrugRepository

UowFactory = Callable[[], UnitOfWork]
RepoFactory = Callable[[UnitOfWork, RequestContext], DrugRepository]
IngredientRepoFactory = Callable[[UnitOfWork], ActiveIngredientRepository]


class CatalogService:
    def __init__(
        self,
        uow_factory: UowFactory,
        repo_factory: RepoFactory,
        ingredient_repo_factory: IngredientRepoFactory,
        audit: AuditLogger,
    ) -> None:
        self._uow_factory = uow_factory
        self._repo_factory = repo_factory
        self._ingredient_repo_factory = ingredient_repo_factory
        self._audit = audit

    async def create_drug(self, data: CreateDrugInput, ctx: RequestContext) -> DrugOutput:
        """Create a drug (with its units and ingredients) for the caller's tenant.

        Raises :class:`ValidationError` on a duplicate unit/ingredient, :class:`NotFoundError`
        when an *ingredients[].ingredient_id* doesn't reference an existing active ingredient,
        and :class:`ConflictError` when *data.barcode* is already registered.
        """
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

            ingredient_repo = self._ingredient_repo_factory(uow)
            try:
                for i in data.ingredients:
                    if await ingredient_repo.get(i.ingredient_id) is None:
                        raise NotFoundError(f"Không tìm thấy hoạt chất {i.ingredient_id}")
                    drug.add_ingredient(
                        DrugIngredient(ingredient_id=i.ingredient_id, amount=i.amount, unit=i.unit)
                    )
            except (DuplicateIngredientError, InvalidIngredientError) as exc:
                raise ValidationError(str(exc)) from exc

            await repo.add(drug)
            await uow.commit()
        await self._record(ctx, AuditAction.CATALOG_DRUG_CREATED, drug.id)
        return DrugOutput.of(drug)

    async def get_drug(self, drug_id: UUID, ctx: RequestContext) -> DrugOutput:
        """Return one drug by id, scoped to the tenant; 404 if not found."""
        require_permission(ctx, "catalog.read")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            drug = await repo.get(drug_id)
        if drug is None:
            raise NotFoundError(f"Không tìm thấy thuốc {drug_id}")
        return DrugOutput.of(drug)

    async def drug_names(self, drug_ids: Sequence[UUID], ctx: RequestContext) -> dict[UUID, str]:
        """Resolve many drug ids to display names in one query.

        Exists for read models that hold ids and need labels — the analytics dashboard
        and reorder screen (docs/19 §4–§5). Deliberately **not** ``NotFoundError`` on an
        unknown id: those screens summarise a period that may pre-date a drug's removal,
        and one stale id must not fail the whole response. Missing ids are absent from
        the returned mapping.
        """
        require_permission(ctx, "catalog.read")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            return await repo.names_by_ids(drug_ids)

    async def get_drug_ingredients(
        self, drug_id: UUID, ctx: RequestContext
    ) -> list[DrugIngredientRef]:
        """Resolve a drug's active ingredients to ``(ingredient_id, name)`` pairs.

        Catalog owns the ``drug_id → ingredients`` mapping; the cross-module safety
        checks (clinical interactions match by name, CRM allergies by ingredient_id)
        both read through here. Raises :class:`NotFoundError` if the drug doesn't
        exist for the tenant, or if a referenced ingredient is missing (a
        data-integrity fault the ``drug_ingredients`` FK should prevent).
        """
        require_permission(ctx, "catalog.read")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            drug = await repo.get(drug_id)
            if drug is None:
                raise NotFoundError(f"Không tìm thấy thuốc {drug_id}")
            ingredient_repo = self._ingredient_repo_factory(uow)
            refs: list[DrugIngredientRef] = []
            for di in drug.ingredients:
                ingredient = await ingredient_repo.get(di.ingredient_id)
                if ingredient is None:
                    raise NotFoundError(f"Không tìm thấy hoạt chất {di.ingredient_id}")
                refs.append(DrugIngredientRef(ingredient_id=di.ingredient_id, name=ingredient.name))
        return refs

    async def create_ingredient(
        self, data: CreateIngredientInput, ctx: RequestContext
    ) -> ActiveIngredientOutput:
        """Create a global active ingredient. Raises :class:`ConflictError` on duplicate name."""
        require_permission(ctx, "catalog.create")
        try:
            ingredient = ActiveIngredient(name=data.name, name_en=data.name_en)
        except InvalidIngredientError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            ingredient_repo = self._ingredient_repo_factory(uow)
            if await ingredient_repo.find_by_name(data.name) is not None:
                raise ConflictError(f"Hoạt chất '{data.name}' đã tồn tại")
            await ingredient_repo.add(ingredient)
            await uow.commit()
        return ActiveIngredientOutput.of(ingredient)

    async def list_ingredients(self, ctx: RequestContext) -> list[ActiveIngredientOutput]:
        """List all global active ingredients (reference data, not tenant-scoped)."""
        require_permission(ctx, "catalog.read")
        async with self._uow_factory() as uow:
            ingredient_repo = self._ingredient_repo_factory(uow)
            ingredients = await ingredient_repo.list()
        return [ActiveIngredientOutput.of(i) for i in ingredients]

    async def list_drugs(
        self,
        ctx: RequestContext,
        *,
        search: str | None = None,
        ids: Sequence[UUID] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DrugOutput]:
        """List the tenant's drugs (name-ordered), paginated by limit/offset.

        ``search`` = substring of the name (case-insensitive) or an exact barcode;
        ``ids`` = a known set, which is how a screen labels a page of rows holding
        drug ids with one request rather than one per row (Sprint 10, D3). Both are
        filters on the same read — no new permission, ``catalog.read`` throughout.
        """
        require_permission(ctx, "catalog.read")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            drugs = await repo.list(search=search, ids=ids, limit=limit, offset=offset)
        return [DrugOutput.of(d) for d in drugs]

    async def _record(self, ctx: RequestContext, action: AuditAction, drug_id: UUID) -> None:
        """Append one audit row — metadata only, never drug/pricing content."""
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=action,
                target_type="drug",
                target_id=str(drug_id),
            ).with_context(client_ip=ctx.client_ip, branch_id=str(ctx.branch_id))
        )
