"""Location use-cases: dựng và sửa sơ đồ kho."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from pharmacy_os.core.audit import AuditAction, AuditEntry, AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import ConflictError, NotFoundError, ValidationError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.location.application.dto import (
    CreateLocationInput,
    LocationOutput,
    UpdateLocationInput,
)
from pharmacy_os.modules.location.domain import (
    Location,
    LocationError,
    LocationKind,
    LocationRepository,
    normalize_code,
)

UowFactory = Callable[[], UnitOfWork]
RepoFactory = Callable[[UnitOfWork, RequestContext], LocationRepository]


class LocationService:
    """Sơ đồ kho — dựng một lần, sửa vài lần một năm.

    Không phát sự kiện nào: sơ đồ là **dữ liệu cấu hình**, không phải dòng nghiệp vụ. Module
    nào cần biết vị trí thì **đọc** qua port của nó, không đợi sự kiện — dựng một đường ống
    sự kiện cho thứ hiếm khi đổi là dựng một đường ống rỗng.
    """

    def __init__(
        self,
        uow_factory: UowFactory,
        repo_factory: RepoFactory,
        audit: AuditLogger,
    ) -> None:
        self._uow_factory = uow_factory
        self._repo_factory = repo_factory
        self._audit = audit

    async def create_location(
        self, data: CreateLocationInput, ctx: RequestContext
    ) -> LocationOutput:
        """Tạo một kho gốc (``parent_id is None``) hoặc một chỗ con.

        Quyền ``location.write``. Trả 404 nếu cha không thuộc chi nhánh; 409 nếu trùng mã
        với anh em cùng cha; 422 nếu mã sai định dạng hoặc lồng sai thứ bậc.
        """
        require_permission(ctx, "location.write")
        try:
            kind = LocationKind(data.kind)
        except ValueError as exc:
            raise ValidationError(f"Tầng vị trí không hợp lệ: {data.kind}") from exc

        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            try:
                ma = normalize_code(data.code)
            except LocationError as exc:
                raise ValidationError(str(exc)) from exc

            # Kiểm trùng TRƯỚC khi dựng aggregate. Đảo thứ tự cũng không hỏng dữ liệu
            # (aggregate bị vứt đi khi ném lỗi), nhưng giữ thứ tự này khiến tính đúng đắn
            # không phụ thuộc vào việc "chưa có gì ghi ở giữa" — một tính chất lần sửa sau
            # có thể phá mà không ai nhận ra. Cùng lý do đã ghi ở
            # `catalog.replace_drug_ingredients`.
            if await repo.by_code_under(data.parent_id, ma) is not None:
                raise ConflictError(f"Mã '{ma}' đã tồn tại trong cùng một chỗ")

            if data.parent_id is None:
                if kind is not LocationKind.WAREHOUSE:
                    raise ValidationError("Vị trí gốc phải là KHO (WAREHOUSE)")
                loc = Location.create_root(
                    tenant_id=ctx.tenant_id,
                    branch_id=ctx.branch_id,
                    code=ma,
                    name=data.name,
                    pick_order=data.pick_order,
                )
            else:
                cha = await repo.get(data.parent_id)
                if cha is None:
                    raise NotFoundError(f"Không tìm thấy vị trí cha {data.parent_id}")
                try:
                    loc = cha.create_child(
                        kind=kind, code=ma, name=data.name, pick_order=data.pick_order
                    )
                except LocationError as exc:
                    raise ValidationError(str(exc)) from exc

            await repo.add(loc)
            await uow.commit()

        await self._record(ctx, AuditAction.LOCATION_CREATED, loc.id, path=loc.path)
        return LocationOutput.of(loc)

    async def update_location(
        self, location_id: UUID, data: UpdateLocationInput, ctx: RequestContext
    ) -> LocationOutput:
        """Đổi tên, thứ tự lấy hàng, hoặc bật/tắt hoạt động. **Mã không đổi được.**"""
        require_permission(ctx, "location.write")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            loc = await repo.get(location_id)
            if loc is None:
                raise NotFoundError(f"Không tìm thấy vị trí {location_id}")

            if data.name is not None:
                loc.rename(data.name)
            if data.pick_order is not None:
                loc.set_pick_order(data.pick_order)
            if data.is_active is not None:
                try:
                    if data.is_active:
                        loc.reactivate()
                    else:
                        loc.deactivate(
                            active_children=await repo.count_active_children(location_id)
                        )
                except LocationError as exc:
                    raise ValidationError(str(exc)) from exc

            await repo.save(loc)
            await uow.commit()

        await self._record(ctx, AuditAction.LOCATION_CHANGED, loc.id, path=loc.path)
        return LocationOutput.of(loc)

    async def list_locations(
        self, ctx: RequestContext, *, include_inactive: bool = False
    ) -> list[LocationOutput]:
        """Toàn bộ sơ đồ của chi nhánh đang đăng nhập.

        Quyền ``location.read`` — ai đứng quầy cũng cần biết thuốc nằm ở đâu, nên đây là
        quyền rộng, khác hẳn ``location.write`` (dựng sơ đồ là việc quản lý).
        """
        require_permission(ctx, "location.read")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            rows = await repo.list_branch(include_inactive=include_inactive)
        return [LocationOutput.of(r) for r in rows]

    async def _record(
        self, ctx: RequestContext, action: AuditAction, location_id: UUID, **extra: str
    ) -> None:
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=action,
                target_type="location",
                target_id=str(location_id),
            ).with_context(client_ip=ctx.client_ip, branch_id=str(ctx.branch_id), **extra)
        )
