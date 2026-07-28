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
    CustomerDataExport,
    CustomerOutput,
    MedicationHistoryItemInput,
    RecordConsentInput,
)
from pharmacy_os.modules.crm.domain import (
    Allergy,
    Condition,
    CrmError,
    Customer,
    CustomerConsent,
    MedicationHistoryEntry,
    MedicationHistorySource,
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
                national_id=data.national_id,
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

    async def export_customer_data(
        self, customer_id: UUID, ctx: RequestContext
    ) -> CustomerDataExport:
        """Everything held about one customer (Luật 91/2025 Điều 13-14).

        Guarded by ``crm.sensitive.read`` because the export contains the health data
        by definition — a right of access exercised at the counter is a pharmacist's
        job, not a cashier's. Recorded as a sensitive read: handing the file over is
        at least as reportable as looking at it.

        Withheld consent is **not** a reason to refuse: the right of access is not
        conditional on consent to processing, and a customer who withdrew is exactly
        the one likely to ask what is still held. The export therefore always
        includes the health data, and always leaves an audit row.
        """
        require_permission(ctx, SENSITIVE_READ)
        customer = await self._get_or_404(customer_id, ctx)
        await self._record(ctx, AuditAction.CUSTOMER_SENSITIVE_READ, customer.id, reason="export")
        return CustomerDataExport(
            customer=CustomerOutput.of(customer, include_sensitive=True),
            exported_at=datetime.now(UTC),
            exported_by=ctx.user_id,
        )

    async def anonymise_customer(self, customer_id: UUID, ctx: RequestContext) -> CustomerOutput:
        """Strip identity and health data, keep the dispensing lines (duyệt Q2).

        This is the erasure request of Luật 91/2025 Điều 13-14, resolved against the
        GPP TT02/2018 I-1a.II.4.d duty to retain records — see
        :meth:`Customer.anonymise` for why neither statute is chosen over the other.

        Deliberately a **separate, explicit** use-case rather than a side effect of
        revoking consent: it cannot be undone, so between "the customer changed their
        mind" and "the data is gone" there is always someone pressing this.
        """
        require_permission(ctx, "crm.erase")
        customer = await self._get_or_404(customer_id, ctx)
        if customer.is_anonymised:
            # Idempotent, and no second audit row: nothing happened this time.
            return CustomerOutput.of(customer)

        customer.anonymise(datetime.now(UTC))
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            await repo.update(customer)
            await uow.commit()
        await self._record(ctx, AuditAction.CUSTOMER_ERASED, customer.id)
        return CustomerOutput.of(customer)

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

    async def record_medication_history(
        self,
        customer_id: UUID,
        items: list[MedicationHistoryItemInput],
        source: MedicationHistorySource,
        ref_id: UUID,
        occurred_at: datetime,
        ctx: RequestContext,
    ) -> int:
        """Append a customer's medication history from a completed sale/dispense.

        A **system reaction**, driven by ``SaleCompleted``/``PrescriptionDispensed``
        at the composition root — so, like :meth:`allergy_severities_for_safety_check`,
        it is deliberately **not** guarded by ``crm.sensitive.write``: the write is
        triggered by whoever completed the sale (often a cashier who must never write
        the health file by hand), and the data comes from the transaction itself, not
        from them typing it.

        Consent is the only lawful basis (Luật 91/2025 Điều 26.1): without a current
        ``HEALTH`` consent this records **nothing** and returns 0 — it never raises,
        so a customer who didn't opt in simply has no history built, and the event
        handler doesn't break. Idempotent on ``(source, ref_id)``: replaying the same
        sale/dispense doesn't duplicate rows. Returns the number of entries written.
        """
        customer = await self._get_or_404(customer_id, ctx)
        if not customer.health_data_allowed:
            return 0
        if any(h.source is source and h.ref_id == ref_id for h in customer.history):
            return 0  # this sale/dispense was already folded in

        recorded = 0
        for item in items:
            if item.quantity <= 0:
                continue
            customer.record_history_entry(
                MedicationHistoryEntry(
                    drug_id=item.drug_id,
                    quantity=item.quantity,
                    source=source,
                    ref_id=ref_id,
                    occurred_at=occurred_at,
                )
            )
            recorded += 1
        if recorded == 0:
            return 0

        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            await repo.update(customer)
            await uow.commit()
        await self._record(
            ctx,
            AuditAction.CUSTOMER_MEDICATION_HISTORY_RECORDED,
            customer.id,
            source=source.value,
            ref_id=str(ref_id),
        )
        return recorded

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
