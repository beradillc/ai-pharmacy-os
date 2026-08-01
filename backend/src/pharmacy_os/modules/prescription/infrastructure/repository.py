"""SQLAlchemy implementation of :class:`PrescriptionRepository`, tenant-scoped."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
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

    async def search(
        self,
        *,
        branch_id: UUID,
        customer_id: UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Prescription]:
        stmt = select(PrescriptionORM).where(
            PrescriptionORM.tenant_id == self._ctx.tenant_id,
            PrescriptionORM.branch_id == branch_id,
        )
        if customer_id is not None:
            stmt = stmt.where(PrescriptionORM.customer_id == customer_id)
        if created_from is not None:
            stmt = stmt.where(PrescriptionORM.created_at >= created_from)
        if created_to is not None:
            stmt = stmt.where(PrescriptionORM.created_at <= created_to)
        if status is not None:
            stmt = stmt.where(PrescriptionORM.status == status)
        stmt = (
            # Cùng khoá phụ `id` với `list_archive`: hai lượt gọi liên tiếp không được cho
            # hai thứ tự khác nhau khi nhiều đơn trùng dấu thời gian — nếu không, phân
            # trang sẽ bỏ sót và lặp dòng mà không ai nhận ra.
            stmt.order_by(PrescriptionORM.created_at.desc(), PrescriptionORM.id.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [to_domain(r) for r in rows]

    async def list_archive(
        self, *, branch_id: UUID | None, limit: int = 50, offset: int = 0
    ) -> Sequence[Prescription]:
        stmt = select(PrescriptionORM).where(
            PrescriptionORM.tenant_id == self._ctx.tenant_id,
            PrescriptionORM.image_data.is_not(None),
        )
        if branch_id is not None:
            stmt = stmt.where(PrescriptionORM.branch_id == branch_id)
        stmt = (
            # `id` làm khoá phụ để hai lượt gọi liên tiếp không cho hai thứ tự khác nhau
            # khi nhiều đơn trùng dấu thời gian.
            stmt.order_by(PrescriptionORM.created_at.desc(), PrescriptionORM.id.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [to_domain(r) for r in rows]

    async def get(self, prescription_id: UUID) -> Prescription | None:
        stmt = select(PrescriptionORM).where(
            PrescriptionORM.id == prescription_id,
            PrescriptionORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_domain(row) if row is not None else None
