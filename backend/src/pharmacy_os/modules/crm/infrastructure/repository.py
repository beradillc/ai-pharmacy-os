"""SQLAlchemy implementation of :class:`CustomerRepository`, tenant-scoped."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import active_blind_index
from pharmacy_os.modules.crm.domain import Customer
from pharmacy_os.modules.crm.infrastructure.mappers import to_domain, to_orm
from pharmacy_os.modules.crm.infrastructure.models import (
    CustomerAllergyORM,
    CustomerConditionORM,
    CustomerConsentORM,
    CustomerMedicationHistoryORM,
    CustomerORM,
)


def _fingerprint(phone: str | None) -> str | None:
    """Searchable fingerprint of *phone*, or ``None`` when there is nothing to index.

    ``None`` covers two different situations on purpose — no phone on the customer,
    and no index key on the deployment — because both mean the same thing to the
    caller: there is no fingerprint to match on, fall back to the column itself.
    """
    if phone is None:
        return None
    index = active_blind_index()
    return index.fingerprint(phone) if index is not None else None


class SqlAlchemyCustomerRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def add(self, customer: Customer) -> None:
        row = to_orm(customer, self._ctx.tenant_id)
        row.phone_fingerprint = _fingerprint(customer.phone)
        self._session.add(row)
        await self._session.flush()

    async def get(self, customer_id: UUID) -> Customer | None:
        stmt = select(CustomerORM).where(
            CustomerORM.id == customer_id, CustomerORM.tenant_id == self._ctx.tenant_id
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_domain(row) if row is not None else None

    async def find_by_phone(self, phone: str) -> Customer | None:
        """Look a customer up by phone, whether or not the column is encrypted.

        With an index key configured the match is on :attr:`phone_fingerprint` — a
        randomised ciphertext differs on every write, so comparing ``phone`` directly
        would never match. Without a key (encryption off, or early in a backfill) it
        falls back to the plain comparison, which is what the column still holds.
        """
        fingerprint = _fingerprint(phone)
        predicate = (
            CustomerORM.phone_fingerprint == fingerprint
            if fingerprint is not None
            else CustomerORM.phone == phone
        )
        stmt = select(CustomerORM).where(predicate, CustomerORM.tenant_id == self._ctx.tenant_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_domain(row) if row is not None else None

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[Customer]:
        stmt = (
            select(CustomerORM)
            .where(CustomerORM.tenant_id == self._ctx.tenant_id)
            .order_by(CustomerORM.full_name)
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [to_domain(r) for r in rows]

    async def update(self, customer: Customer) -> None:
        """Persist scalar-field changes and append any new allergy/condition/history
        children. Domain child collections are insert-only (no edit/remove use-case
        exists yet), so reconciling by id-diff is sufficient and avoids clobbering
        rows a concurrent request may have already inserted.
        """
        stmt = select(CustomerORM).where(
            CustomerORM.id == customer.id, CustomerORM.tenant_id == self._ctx.tenant_id
        )
        row = (await self._session.execute(stmt)).scalar_one()
        row.full_name = customer.full_name
        row.phone = customer.phone
        # Kept in step here rather than in the mapper: the fingerprint is a storage
        # concern (it exists only so an encrypted column stays searchable), and the
        # mapper is a pure translation the domain also uses.
        row.phone_fingerprint = _fingerprint(customer.phone)
        row.dob = customer.dob
        row.gender = customer.gender
        row.weight_kg = customer.weight_kg
        row.national_id_hash = customer.national_id_hash
        row.anonymised_at = customer.anonymised_at

        # Anonymisation empties these collections; the id-diff below is insert-only,
        # so the deletions have to be applied explicitly or the rows would survive
        # the erasure request that removed them from the aggregate.
        if customer.is_anonymised:
            row.allergies.clear()
            row.conditions.clear()

        existing_consent_ids = {k.id for k in row.consents}
        for k in customer.consents:
            if k.id not in existing_consent_ids:
                row.consents.append(
                    CustomerConsentORM(
                        id=k.id,
                        customer_id=customer.id,
                        purpose=k.purpose.value,
                        granted=k.granted,
                        terms_version=k.terms_version,
                        recorded_at=k.recorded_at,
                        actor_user_id=k.actor_user_id,
                        client_ip=k.client_ip,
                    )
                )

        existing_allergy_ids = {a.id for a in row.allergies}
        for a in customer.allergies:
            if a.id not in existing_allergy_ids:
                row.allergies.append(
                    CustomerAllergyORM(
                        id=a.id,
                        customer_id=customer.id,
                        ingredient_id=a.ingredient_id,
                        severity=a.severity.value,
                        note=a.note,
                    )
                )

        existing_condition_ids = {c.id for c in row.conditions}
        for c in customer.conditions:
            if c.id not in existing_condition_ids:
                row.conditions.append(
                    CustomerConditionORM(
                        id=c.id,
                        customer_id=customer.id,
                        condition_code=c.condition_code,
                        note=c.note,
                    )
                )

        existing_history_ids = {h.id for h in row.history}
        for h in customer.history:
            if h.id not in existing_history_ids:
                row.history.append(
                    CustomerMedicationHistoryORM(
                        id=h.id,
                        customer_id=customer.id,
                        drug_id=h.drug_id,
                        quantity=h.quantity,
                        source=h.source.value,
                        ref_id=h.ref_id,
                        occurred_at=h.occurred_at,
                    )
                )

        await self._session.flush()
