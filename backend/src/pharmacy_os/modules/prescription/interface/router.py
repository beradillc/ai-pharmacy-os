"""Prescription HTTP endpoints (intake, pharmacist validate/reject, dispense)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.prescription.application import PrescriptionService
from pharmacy_os.modules.prescription.interface.schemas import (
    AttachPrescriptionImageRequest,
    CreatePrescriptionRequest,
    PrescriptionImageResponse,
    PrescriptionResponse,
    RejectPrescriptionRequest,
)

ContextDep = Callable[..., Awaitable[RequestContext]]
"""``get_context`` là **async** kể từ audit B-07: nó phải tra CSDL để xác nhận cặp
``(tenant, chi nhánh)`` là có thật. FastAPI tự await, nên route không phải đổi gì."""


def _service(request: Request) -> PrescriptionService:
    service: PrescriptionService = request.app.state.container.resolve(PrescriptionService)
    return service


def build_router(get_context: ContextDep) -> APIRouter:
    root = APIRouter(prefix="/prescriptions", tags=["prescription"])

    @root.post("", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
    async def create_prescription(
        body: CreatePrescriptionRequest,
        service: PrescriptionService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PrescriptionResponse:
        return PrescriptionResponse.of(await service.create_prescription(body.to_input(), ctx))

    @root.get("/archive", response_model=list[PrescriptionResponse])
    async def list_archive(
        service: PrescriptionService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> list[PrescriptionResponse]:
        """Đơn thuốc **đã có ảnh**, mới nhất trước — nguồn của màn Cài đặt → Lưu trữ.

        Đặt TRƯỚC ``/{prescription_id}``: FastAPI khớp route theo thứ tự khai báo, nên nếu
        đặt sau thì ``archive`` sẽ bị nuốt thành một ``prescription_id`` và trả 422 vì
        không phải UUID.

        Quyền ``rx.image.read``; thêm ``archive.read.chain`` thì thấy **toàn bộ chi nhánh**.
        """
        return [
            PrescriptionResponse.of(o)
            for o in await service.list_archive(ctx, limit=limit, offset=offset)
        ]

    @root.get("/{prescription_id}", response_model=PrescriptionResponse)
    async def get_prescription(
        prescription_id: UUID,
        service: PrescriptionService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PrescriptionResponse:
        return PrescriptionResponse.of(await service.get_prescription(prescription_id, ctx))

    @root.post("/{prescription_id}/validate", response_model=PrescriptionResponse)
    async def validate_prescription(
        prescription_id: UUID,
        service: PrescriptionService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PrescriptionResponse:
        return PrescriptionResponse.of(await service.validate_prescription(prescription_id, ctx))

    @root.post("/{prescription_id}/reject", response_model=PrescriptionResponse)
    async def reject_prescription(
        prescription_id: UUID,
        body: RejectPrescriptionRequest,
        service: PrescriptionService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PrescriptionResponse:
        return PrescriptionResponse.of(
            await service.reject_prescription(prescription_id, body.reason, ctx)
        )

    @root.post("/{prescription_id}/dispense", response_model=PrescriptionResponse)
    async def dispense_prescription(
        prescription_id: UUID,
        service: PrescriptionService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PrescriptionResponse:
        return PrescriptionResponse.of(await service.dispense_prescription(prescription_id, ctx))

    @root.put("/{prescription_id}/image", response_model=PrescriptionResponse)
    async def attach_image(
        prescription_id: UUID,
        body: AttachPrescriptionImageRequest,
        service: PrescriptionService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PrescriptionResponse:
        """Gắn ảnh đơn thuốc gốc đã chụp ở quầy. Ghi đè ảnh cũ nếu có.

        ``PUT`` chứ không ``POST``: thân yêu cầu **là** ảnh của đơn này, đầy đủ, nên gọi
        hai lần cùng một thân cho cùng một kết quả — chụp lại vì trượt nét là ca dùng thật.

        Quyền ``rx.create``: chụp và nộp một tờ giấy khác hẳn việc đọc chẩn đoán trong đó.
        Trả 404 nếu đơn không thuộc nhà thuốc; **422** nếu ảnh sai định dạng, rỗng, base64
        hỏng, hoặc quá 2 MB sau giải mã.
        """
        return PrescriptionResponse.of(
            await service.attach_image(prescription_id, body.image_data, body.content_type, ctx)
        )

    @root.get("/{prescription_id}/image", response_model=PrescriptionImageResponse)
    async def get_image(
        prescription_id: UUID,
        service: PrescriptionService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PrescriptionImageResponse:
        """Đọc nội dung ảnh đơn thuốc. **Mỗi lượt đọc ghi một dòng `RX_IMAGE_VIEWED`.**

        Đường riêng, không gộp vào ``GET /prescriptions/{id}``: gộp thì mọi lượt xem đơn
        đều kéo theo dữ liệu nhạy cảm, và dòng audit *"ai đã xem ảnh"* mất hết nghĩa vì ai
        mở đơn cũng thành người đã xem ảnh.

        Quyền ``rx.image.read`` (cấp Dược sĩ và cấp chuỗi, **không** cho Thu ngân — ảnh
        mang chẩn đoán). Trả 404 nếu đơn không tồn tại **hoặc chưa có ảnh**.
        """
        return PrescriptionImageResponse.of(await service.get_image(prescription_id, ctx))

    return root
