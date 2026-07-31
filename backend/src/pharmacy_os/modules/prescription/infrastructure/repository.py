"""SQLAlchemy implementation of :class:`PrescriptionRepository`, tenant-scoped."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.prescription.domain import Prescription
from pharmacy_os.modules.prescription.infrastructure.mappers import to_domain, to_orm
from pharmacy_os.modules.prescription.infrastructure.models import PrescriptionORM


class SqlAlchemyPrescriptionRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def add(self, prescription: Prescription) -> None:
        self._session.add(to_orm(prescription))
        await self._session.flush()

    async def update(self, prescription: Prescription) -> None:
        stmt = select(PrescriptionORM).where(
            PrescriptionORM.id == prescription.id,
            PrescriptionORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one()
        row.status = prescription.status.value
        row.validated_by = prescription.validated_by
        row.rejection_reason = prescription.rejection_reason
        await self._session.flush()

    async def save_image(self, prescription: Prescription) -> None:
        stmt = select(PrescriptionORM).where(
            PrescriptionORM.id == prescription.id,
            PrescriptionORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one()
        row.image_data = prescription.image_data
        row.image_content_type = prescription.image_content_type
        await self._session.flush()

    async def get(self, prescription_id: UUID) -> Prescription | None:
        stmt = select(PrescriptionORM).where(
            PrescriptionORM.id == prescription_id,
            PrescriptionORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_domain(row) if row is not None else None
