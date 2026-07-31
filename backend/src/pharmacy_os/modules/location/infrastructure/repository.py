"""Cài đặt :class:`LocationRepository` bằng SQLAlchemy, phạm vi theo chi nhánh."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.location.domain import Location
from pharmacy_os.modules.location.infrastructure.mappers import to_domain, to_orm
from pharmacy_os.modules.location.infrastructure.models import LocationORM


class SqlAlchemyLocationRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    def _scope(self) -> tuple[ColumnElement[bool], ColumnElement[bool]]:
        """Bộ lọc tenant + chi nhánh dùng cho MỌI truy vấn của repo này.

        Gom vào một chỗ để không có truy vấn nào quên một trong hai — quên `tenant_id` là
        rò dữ liệu sang nhà thuốc khác, quên `branch_id` là trộn sơ đồ hai cơ sở.
        """
        return (
            LocationORM.tenant_id == self._ctx.tenant_id,
            LocationORM.branch_id == self._ctx.branch_id,
        )

    async def add(self, location: Location) -> None:
        self._session.add(to_orm(location))
        await self._session.flush()

    async def get(self, location_id: UUID) -> Location | None:
        stmt = select(LocationORM).where(LocationORM.id == location_id, *self._scope())
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_domain(row) if row is not None else None

    async def save(self, location: Location) -> None:
        """Ghi lại **tên, thứ tự lấy hàng, trạng thái**. Cổng hẹp — xem port.

        Không dùng ``to_orm()``: nó dựng một row MỚI mang mọi trường, nên ``merge`` sẽ ghi
        đè cả ``code`` và ``path`` — hai thứ bất biến. Đúng cái bẫy đã ghi ở
        ``catalog.save_ingredients``.
        """
        stmt = select(LocationORM).where(LocationORM.id == location.id, *self._scope())
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return
        row.name = location.name
        row.pick_order = location.pick_order
        row.is_active = location.is_active
        await self._session.flush()

    async def by_code_under(self, parent_id: UUID | None, code: str) -> Location | None:
        stmt = select(LocationORM).where(
            LocationORM.parent_id.is_(None)
            if parent_id is None
            else LocationORM.parent_id == parent_id,
            LocationORM.code == code,
            *self._scope(),
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_domain(row) if row is not None else None

    async def list_branch(self, *, include_inactive: bool = False) -> Sequence[Location]:
        stmt = select(LocationORM).where(*self._scope())
        if not include_inactive:
            stmt = stmt.where(LocationORM.is_active.is_(True))
        # Sắp theo `pick_order` TRƯỚC rồi mới tới `path`: thứ tự đi lấy hàng là thứ người
        # dùng cần, còn `path` chỉ là khoá phụ để hai lượt gọi không cho hai thứ tự khác
        # nhau khi `pick_order` bằng nhau (mặc định cả kho đều là 0).
        stmt = stmt.order_by(LocationORM.pick_order, LocationORM.path)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [to_domain(r) for r in rows]

    async def count_active_children(self, location_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(LocationORM)
            .where(
                LocationORM.parent_id == location_id,
                LocationORM.is_active.is_(True),
                *self._scope(),
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())
