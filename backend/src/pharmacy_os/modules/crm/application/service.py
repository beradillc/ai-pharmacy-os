"""Crm use-cases: customer intake, consent, allergy/condition recording.

The service depends only on ports; the concrete repository and unit of work are
injected as factories at composition time (see the module ``register``).

Two rules run through every use-case here, both from the feature's compliance gate
(``docs/features/ho-so-suc-khoe-khach-hang/01_DECISIONS.md``):

* **Reading health data needs its own permission.** ``crm.read`` sees name and phone;
  ``crm.sensitive.read`` sees allergies, conditions and medication history. NĐ356
  Điều 4.2 requires sensitive data to sit behind restricted access of its own, and
  GPP TT02 I-1a.III.4.a obliges counter staff to keep patient information secret —
  which is hard to do while looking at it.
* **Every touch of health data lands in ``audit_logs``.** Reads included: an access
  log that only records writes cannot answer "who looked at this patient's file",
  which is the question an inspection actually asks.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from pharmacy_os.core.audit import AuditAction, AuditEntry, AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import NotFoundError, ValidationError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.crm.application.dto import (
    AddAllergyInput,
    AddConditionInput,
    CreateCustomerInput,
    CustomerOutput,
    RecordConsentInput,
)
from pharmacy_os.modules.crm.domain import (
    Allergy,
    Condition,
    CrmError,
    Customer,
    CustomerConsent,
)
from pharmacy_os.modules.crm.domain.ports import CustomerRepository

UowFactory = Callable[[], UnitOfWork]
RepoFactory = Callable[[UnitOfWork, RequestContext], CustomerRepository]


SENSITIVE_READ = "crm.sensitive.read"
SENSITIVE_WRITE = "crm.sensitive.write"


class CrmService:
    def __init__(
        self, uow_factory: UowFactory, repo_factory: RepoFactory, audit: AuditLogger
    ) -> None:
        self._uow_factory = uow_factory
        self._repo_factory = repo_factory
        self._audit = audit

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

        Ingredient existence is enforced by the DB foreign key to
        ``active_ingredients`` (no cross-module read here — validating via
        catalog's own repository would require crm to depend on catalog, which
        is a composition-root cross-module step gated behind Opus, not done in
        this step). The FK violation is caught here and translated to a 404
        instead of leaking a raw integrity error: ``customer_id`` is already
        confirmed to exist by ``_get_or_404`` above, so an ``IntegrityError`` at
        this insert can only come from the ``ingredient_id`` FK.
        """
        require_permission(ctx, SENSITIVE_WRITE)
        customer = await self._get_or_404(customer_id, ctx)
        try:
            customer.add_allergy(
                Allergy(ingredient_id=data.ingredient_id, severity=data.severity, note=data.note)
            )
        except CrmError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            try:
                await repo.update(customer)
            except IntegrityError as exc:
                raise NotFoundError(f"Không tìm thấy hoạt chất {data.ingredient_id}") from exc
            await uow.commit()
        await self._record(ctx, AuditAction.CUSTOMER_SENSITIVE_WRITE, customer.id, field="allergy")
        return CustomerOutput.of(customer)

    async def add_condition(
        self, customer_id: UUID, data: AddConditionInput, ctx: RequestContext
    ) -> CustomerOutput:
        """Record a customer's pre-existing condition (ICD-10, dedup by code)."""
        require_permission(ctx, SENSITIVE_WRITE)
        customer = await self._get_or_404(customer_id, ctx)
        try:
            customer.add_condition(Condition(condition_code=data.condition_code, note=data.note))
        except CrmError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            await repo.update(customer)
            await uow.commit()
        await self._record(
            ctx, AuditAction.CUSTOMER_SENSITIVE_WRITE, customer.id, field="condition"
        )
        return CustomerOutput.of(customer)

    async def record_consent(
        self, customer_id: UUID, data: RecordConsentInput, ctx: RequestContext
    ) -> CustomerOutput:
        """Append a consent decision taken at the counter on the customer's behalf.

        Granting and revoking are the same use-case with ``granted`` flipped, because
        both are the same fact — "on this date, this staff account recorded this
        decision" — and both must leave a row (Luật 91/2025 Điều 9).

        Revoking ``HEALTH`` deliberately does **not** delete anything: erasure is a
        separate, explicit act (duyệt Q2), so that between "the customer withdrew
        consent" and "the data is gone" there is always a human pressing something —
        anonymisation cannot be undone.
        """
        require_permission(ctx, "crm.consent.manage")
        customer = await self._get_or_404(customer_id, ctx)
        try:
            customer.record_consent(
                CustomerConsent(
                    purpose=data.purpose,
                    granted=data.granted,
                    terms_version=data.terms_version,
                    recorded_at=datetime.now(UTC),
                    actor_user_id=ctx.user_id,
                    client_ip=ctx.client_ip,
                )
            )
        except CrmError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            await repo.update(customer)
            await uow.commit()
        await self._record(
            ctx,
            AuditAction.CONSENT_GRANTED if data.granted else AuditAction.CONSENT_REVOKED,
            customer.id,
            purpose=data.purpose.value,
            terms_version=data.terms_version,
        )
        return CustomerOutput.of(customer)

    async def get_customer(self, customer_id: UUID, ctx: RequestContext) -> CustomerOutput:
        """Return one customer, with health data only if the caller may see it.

        Missing ``crm.sensitive.read`` is answered by withholding the fields, not by
        403: a cashier attaching a customer to a sale is doing something legitimate
        and should not be told "forbidden" for the part they never asked for.
        """
        require_permission(ctx, "crm.read")
        customer = await self._get_or_404(customer_id, ctx)
        include = self._may_read_sensitive(customer, ctx)
        if include:
            await self._record(ctx, AuditAction.CUSTOMER_SENSITIVE_READ, customer.id)
        return CustomerOutput.of(customer, include_sensitive=include)

    async def list_customers(
        self, ctx: RequestContext, *, limit: int = 50, offset: int = 0
    ) -> list[CustomerOutput]:
        """List the tenant's customers (name-ordered), paginated by limit/offset.

        The list **never** carries health data, whatever the caller holds: a page of
        fifty patient files is not a lookup, and auditing it as fifty separate reads
        would drown the trail. Open one customer to see their record.
        """
        require_permission(ctx, "crm.read")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            customers = await repo.list(limit=limit, offset=offset)
        return [CustomerOutput.of(c, include_sensitive=False) for c in customers]

    async def allergy_severities_for_safety_check(
        self, customer_id: UUID, ctx: RequestContext
    ) -> dict[UUID, str]:
        """Ingredient → severity, for the automated clinical safety check only.

        Deliberately **not** guarded by ``crm.sensitive.read`` (duyệt Q3). The check
        runs on a sale completed by whoever is at the till — often a cashier who must
        not see diagnoses — and refusing it would mean an allergy warning silently
        stops firing for exactly the staff least able to catch the problem
        themselves. Patient safety wins over need-to-know here, and the trade is paid
        for in two ways: the caller gets ingredient ids and severities, never the
        record, the names, or the conditions (data minimisation); and every call
        lands in the audit trail under its own action, so machine reads stay
        distinguishable from a person opening the file.

        Consent is still required — without it there is no lawful basis to process
        the data at all, and an empty result simply means no warning can be raised.
        """
        customer = await self._get_or_404(customer_id, ctx)
        if not customer.health_data_allowed:
            return {}
        await self._record(ctx, AuditAction.CUSTOMER_SENSITIVE_AUTO_CHECK, customer.id)
        return {a.ingredient_id: a.severity.value for a in customer.allergies}

    def _may_read_sensitive(self, customer: Customer, ctx: RequestContext) -> bool:
        """Permission **and** a lawful basis — both, or the data stays hidden.

        Consent is the only basis for processing this data (Luật 91/2025 Điều 26.1),
        so a staff member holding the permission still may not read the file of a
        customer who never agreed, or who withdrew.
        """
        return ctx.has(SENSITIVE_READ) and customer.health_data_allowed

    async def _record(
        self,
        ctx: RequestContext,
        action: AuditAction,
        customer_id: UUID,
        **extra: str,
    ) -> None:
        """Append one audit row.

        ``context`` carries metadata only — which field was touched, which consent
        purpose — never the values. Copying diagnoses into the audit trail would make
        it a second, less guarded store of the data it exists to protect.
        """
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=action,
                target_type="customer",
                target_id=str(customer_id),
            ).with_context(client_ip=ctx.client_ip, branch_id=str(ctx.branch_id), **extra)
        )

    async def _get_or_404(self, customer_id: UUID, ctx: RequestContext) -> Customer:
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            customer = await repo.get(customer_id)
        if customer is None:
            raise NotFoundError(f"Không tìm thấy khách hàng {customer_id}")
        return customer
