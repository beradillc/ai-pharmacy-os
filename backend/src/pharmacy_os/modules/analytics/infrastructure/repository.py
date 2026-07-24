"""SQLAlchemy implementation of :class:`ReorderSuggestionRepository`, tenant-scoped."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.analytics.domain import ReorderSuggestion, SuggestionStatus
from pharmacy_os.modules.analytics.infrastructure.mappers import to_domain, to_orm
from pharmacy_os.modules.analytics.infrastructure.models import ReorderSuggestionORM

# Statuses a fresh reorder run regenerates (the terminal ones are kept as history).
_RECOMPUTABLE = (SuggestionStatus.PENDING.value, SuggestionStatus.INSUFFICIENT_DATA.value)


class SqlAlchemyReorderSuggestionRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def add(self, suggestion: ReorderSuggestion) -> None:
        self._session.add(to_orm(suggestion))
        await self._session.flush()

    async def get(self, suggestion_id: UUID) -> ReorderSuggestion | None:
        stmt = select(ReorderSuggestionORM).where(
            ReorderSuggestionORM.id == suggestion_id,
            ReorderSuggestionORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_domain(row) if row is not None else None

    async def update(self, suggestion: ReorderSuggestion) -> None:
        stmt = select(ReorderSuggestionORM).where(
            ReorderSuggestionORM.id == suggestion.id,
            ReorderSuggestionORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one()
        row.status = suggestion.status.value
        row.po_id = suggestion.po_id
        await self._session.flush()

    async def list_by_branch(
        self, tenant_id: UUID, branch_id: UUID, *, status: SuggestionStatus | None = None
    ) -> list[ReorderSuggestion]:
        stmt = select(ReorderSuggestionORM).where(
            ReorderSuggestionORM.tenant_id == tenant_id,
            ReorderSuggestionORM.branch_id == branch_id,
        )
        if status is not None:
            stmt = stmt.where(ReorderSuggestionORM.status == status.value)
        stmt = stmt.order_by(ReorderSuggestionORM.suggested_qty.desc())
        rows = (await self._session.execute(stmt)).scalars().all()
        return [to_domain(r) for r in rows]

    async def count_by_status(
        self, tenant_id: UUID, branch_id: UUID, status: SuggestionStatus
    ) -> int:
        stmt = select(func.count(ReorderSuggestionORM.id)).where(
            ReorderSuggestionORM.tenant_id == tenant_id,
            ReorderSuggestionORM.branch_id == branch_id,
            ReorderSuggestionORM.status == status.value,
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def delete_recomputable_for_branch(self, tenant_id: UUID, branch_id: UUID) -> None:
        stmt = delete(ReorderSuggestionORM).where(
            ReorderSuggestionORM.tenant_id == tenant_id,
            ReorderSuggestionORM.branch_id == branch_id,
            ReorderSuggestionORM.status.in_(_RECOMPUTABLE),
        )
        await self._session.execute(stmt)
        await self._session.flush()
