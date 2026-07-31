"""HTTP endpoint cho sơ đồ kho."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.location.application import LocationService
from pharmacy_os.modules.location.interface.schemas import (
    CreateLocationRequest,
    LocationResponse,
    UpdateLocationRequest,
)

ContextDep = Callable[..., Awaitable[RequestContext]]


def _service(request: Request) -> LocationService:
    service: LocationService = request.app.state.container.resolve(LocationService)
    return service


def build_router(get_context: ContextDep) -> APIRouter:
    router = APIRouter(prefix="/locations", tags=["location"])

    @router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
    async def create_location(
        body: CreateLocationRequest,
        service: LocationService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> LocationResponse:
        """Tạo một vị trí lưu trữ.

        ``parent_id: null`` tạo một **KHO** gốc; khác null tạo chỗ con bên dưới.

        Quyền ``location.write``. Trả **409** nếu trùng mã với anh em cùng cha (ô "01" dưới
        kệ A và dưới kệ B là hai chỗ khác nhau — trùng ở hai cha khác nhau là hợp lệ);
        **422** nếu mã sai định dạng hoặc lồng sai thứ bậc; **404** nếu cha không thuộc
        chi nhánh đang đăng nhập.
        """
        return LocationResponse.of(await service.create_location(body.to_input(), ctx))

    @router.get("", response_model=list[LocationResponse])
    async def list_locations(
        service: LocationService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
        include_inactive: bool = Query(default=False),
    ) -> list[LocationResponse]:
        """Sơ đồ kho của chi nhánh đang đăng nhập, sắp theo **thứ tự đi lấy hàng**.

        Trả về danh sách phẳng kèm ``parent_id`` và ``path`` — màn hình dựng cây từ đó mà
        không cần endpoint đệ quy, và thứ tự trả về đã là thứ tự người ta đi trong kho.

        Quyền ``location.read`` (rộng: ai đứng quầy cũng cần biết thuốc nằm ở đâu).
        """
        return [
            LocationResponse.of(o)
            for o in await service.list_locations(ctx, include_inactive=include_inactive)
        ]

    @router.patch("/{location_id}", response_model=LocationResponse)
    async def update_location(
        location_id: UUID,
        body: UpdateLocationRequest,
        service: LocationService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> LocationResponse:
        """Đổi tên, thứ tự lấy hàng, hoặc bật/tắt hoạt động.

        ``PATCH`` chứ không ``PUT``: thân yêu cầu là **tập con** các trường muốn đổi, và
        ``code``/``path`` không nằm trong đó vì chúng bất biến.

        Trả **422** khi ngừng hoạt động một vị trí còn chỗ con đang hoạt động — ngừng cha
        mà để con lại tạo ra những ô vẫn nhận hàng dưới một kệ đã khai tử.
        """
        return LocationResponse.of(await service.update_location(location_id, body.to_input(), ctx))

    return router
