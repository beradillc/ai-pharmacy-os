"""Crm use-cases: customer intake, allergy/condition recording.

The service depends only on ports; the concrete repository and unit of work are
injected as factories at composition time (see the module ``register``).
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import NotFoundError, ValidationError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.crm.application.dto import (
    AddAllergyInput,
    AddConditionInput,
    CreateCustomerInput,
    CustomerOutput,
)
from pharmacy_os.modules.crm.domain import Allergy, Condition, CrmError, Customer
from pharmacy_os.modules.crm.domain.ports import CustomerRepository

UowFactory = Callable[[], UnitOfWork]
RepoFactory = Callable[[UnitOfWork, RequestContext], CustomerRepository]


class CrmService:
    def __init__(self, uow_factory: UowFactory, repo_factory: RepoFactory) -> None:
        self._uow_factory = uow_factory
        self._repo_factory = repo_factory

    async def create_customer(
        self, data: CreateCustomerInput, ctx: RequestContext
    ) -> CustomerOutput:
        """Register a new customer/patient for the caller's tenant."""
        require_permission(ctx, "crm.create")
        try:
            customer = Customer(
                full_name=data.full_name,
                phone=data.phone,
                dob=data.dob,
                gender=data.gender,
                weight_kg=data.weight_kg,
                national_id_hash=data.national_id_hash,
            )
        except CrmError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            await repo.add(customer)
            await uow.commit()
        return CustomerOutput.of(customer)

    async def add_allergy(
        self, customer_id: UUID, data: AddAllergyInput, ctx: RequestContext
    ) -> CustomerOutput:
        """Record a customer's allergy to an active ingredient (dedup by ingredient_id).

        Ingredient existence is enforced only by the DB foreign key to
        ``active_ingredients`` — there is no cross-module read here (out of scope
        for this step). An unknown ``ingredient_id`` surfaces as a raw integrity
        error on live Postgres, not a friendly 404/422; SQLite (tests) doesn't
        enforce the FK at all. See ``crm/infrastructure/models.py``.
        """
        require_permission(ctx, "crm.write")
        customer = await self._get_or_404(customer_id, ctx)
        try:
            customer.add_allergy(
                Allergy(ingredient_id=data.ingredient_id, severity=data.severity, note=data.note)
            )
        except CrmError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            await repo.update(customer)
            await uow.commit()
        return CustomerOutput.of(customer)

    async def add_condition(
        self, customer_id: UUID, data: AddConditionInput, ctx: RequestContext
    ) -> CustomerOutput:
        """Record a customer's pre-existing condition (ICD-10, dedup by code)."""
        require_permission(ctx, "crm.write")
        customer = await self._get_or_404(customer_id, ctx)
        try:
            customer.add_condition(Condition(condition_code=data.condition_code, note=data.note))
        except CrmError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            await repo.update(customer)
            await uow.commit()
        return CustomerOutput.of(customer)

    async def get_customer(self, customer_id: UUID, ctx: RequestContext) -> CustomerOutput:
        """Return one customer by id, scoped to the tenant; 404 if not found."""
        require_permission(ctx, "crm.read")
        customer = await self._get_or_404(customer_id, ctx)
        return CustomerOutput.of(customer)

    async def list_customers(
        self, ctx: RequestContext, *, limit: int = 50, offset: int = 0
    ) -> list[CustomerOutput]:
        """List the tenant's customers (name-ordered), paginated by limit/offset."""
        require_permission(ctx, "crm.read")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            customers = await repo.list(limit=limit, offset=offset)
        return [CustomerOutput.of(c) for c in customers]

    async def _get_or_404(self, customer_id: UUID, ctx: RequestContext) -> Customer:
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            customer = await repo.get(customer_id)
        if customer is None:
            raise NotFoundError(f"Không tìm thấy khách hàng {customer_id}")
        return customer
