"""Prescription use-cases: intake, pharmacist validation/rejection, dispense.

The service depends only on ports; the concrete repository and unit of work are
injected as factories at composition time (see the module ``register``).
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from pharmacy_os.core.audit import AuditAction, AuditEntry, AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import NotFoundError, ValidationError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.prescription.application.dto import (
    CreatePrescriptionInput,
    PrescriptionImageOutput,
    PrescriptionOutput,
)
from pharmacy_os.modules.prescription.domain import (
    Prescription,
    PrescriptionDispensed,
    PrescriptionError,
    PrescriptionItem,
    PrescriptionRejected,
    PrescriptionValidated,
)
from pharmacy_os.modules.prescription.domain.ports import PrescriptionRepository

UowFactory = Callable[[], UnitOfWork]
RepoFactory = Callable[[UnitOfWork, RequestContext], PrescriptionRepository]


class PrescriptionService:
    def __init__(
        self, uow_factory: UowFactory, repo_factory: RepoFactory, audit: AuditLogger
    ) -> None:
        self._uow_factory = uow_factory
        self._repo_factory = repo_factory
        self._audit = audit

    async def create_prescription(
        self, data: CreatePrescriptionInput, ctx: RequestContext
    ) -> PrescriptionOutput:
        """Record a prescription intake (DRAFT) with its items."""
        require_permission(ctx, "rx.create")

        rx = Prescription(
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            customer_id=data.customer_id,
            doctor_name=data.doctor_name,
            source=data.source,
            doctor_license=data.doctor_license,
            diagnosis=data.diagnosis,
            image_url=data.image_url,
        )
        try:
            for item in data.items:
                rx.add_item(
                    PrescriptionItem(
                        drug_id=item.drug_id,
                        quantity=item.quantity,
                        dose=item.dose,
                        frequency=item.frequency,
                        duration=item.duration,
                        instructions=item.instructions,
                    )
                )
        except PrescriptionError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            await repo.add(rx)
            await uow.commit()

        await self._record(ctx, AuditAction.PRESCRIPTION_CREATED, rx.id)
        return PrescriptionOutput.of(rx)

    async def validate_prescription(
        self, prescription_id: UUID, ctx: RequestContext
    ) -> PrescriptionOutput:
        """Pharmacist approval: DRAFT -> VALIDATED. Emits ``PrescriptionValidated``."""
        require_permission(ctx, "rx.approve")
        rx = await self._get_or_404(prescription_id, ctx)
        try:
            rx.validate(validated_by=ctx.user_id)
        except PrescriptionError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            await repo.update(rx)
            uow.collect(
                PrescriptionValidated(
                    tenant_id=ctx.tenant_id,
                    prescription_id=rx.id,
                    validated_by=ctx.user_id,
                )
            )
            await uow.commit()

        await self._record(ctx, AuditAction.PRESCRIPTION_APPROVED, rx.id)
        return PrescriptionOutput.of(rx)

    async def reject_prescription(
        self, prescription_id: UUID, reason: str, ctx: RequestContext
    ) -> PrescriptionOutput:
        """Pharmacist rejection (invalid intake or risk found). Emits ``PrescriptionRejected``."""
        require_permission(ctx, "rx.approve")
        rx = await self._get_or_404(prescription_id, ctx)
        try:
            rx.reject(reason)
        except PrescriptionError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            await repo.update(rx)
            uow.collect(
                PrescriptionRejected(tenant_id=ctx.tenant_id, prescription_id=rx.id, reason=reason)
            )
            await uow.commit()

        await self._record(ctx, AuditAction.PRESCRIPTION_REJECTED, rx.id)
        return PrescriptionOutput.of(rx)

    async def dispense_prescription(
        self, prescription_id: UUID, ctx: RequestContext
    ) -> PrescriptionOutput:
        """Mark a validated prescription DISPENSED. Emits ``PrescriptionDispensed``."""
        require_permission(ctx, "rx.dispense")
        rx = await self._get_or_404(prescription_id, ctx)
        try:
            rx.dispense()
        except PrescriptionError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            await repo.update(rx)
            uow.collect(PrescriptionDispensed(tenant_id=ctx.tenant_id, prescription_id=rx.id))
            await uow.commit()

        await self._record(ctx, AuditAction.PRESCRIPTION_DISPENSED, rx.id)
        return PrescriptionOutput.of(rx)

    async def get_prescription(
        self, prescription_id: UUID, ctx: RequestContext
    ) -> PrescriptionOutput:
        """Return one prescription by id, scoped to the tenant; 404 if not found."""
        require_permission(ctx, "rx.read")
        rx = await self._get_or_404(prescription_id, ctx)
        return PrescriptionOutput.of(rx)

    async def attach_image(
        self, prescription_id: UUID, image_data: str, content_type: str, ctx: RequestContext
    ) -> PrescriptionOutput:
        """Gắn ảnh đơn thuốc gốc đã chụp ở quầy.

        Quyền ``rx.create`` — ai lập được đơn thì gắn được ảnh của chính đơn đó. **Không**
        đòi ``rx.image.read``: chụp và nộp một tờ giấy khác hẳn việc đọc chẩn đoán trong đó,
        và người đứng quầy phải làm được việc thứ nhất.

        Raises :class:`NotFoundError` nếu đơn không thuộc tenant; :class:`ValidationError`
        nếu ảnh sai định dạng, rỗng, base64 hỏng, hoặc quá 2 MB.
        """
        require_permission(ctx, "rx.create")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            rx = await repo.get(prescription_id)
            if rx is None:
                raise NotFoundError(f"Không tìm thấy đơn thuốc {prescription_id}")
            try:
                rx.attach_image(image_data, content_type)
            except PrescriptionError as exc:
                raise ValidationError(str(exc)) from exc
            await repo.save_image(rx)
            await uow.commit()

        await self._record(
            ctx,
            AuditAction.RX_IMAGE_ATTACHED,
            rx.id,
            content_type=content_type,
            approx_bytes=str(len(image_data) * 3 // 4),
        )
        return PrescriptionOutput.of(rx)

    async def get_image(
        self, prescription_id: UUID, ctx: RequestContext
    ) -> PrescriptionImageOutput:
        """Đọc nội dung ảnh đơn thuốc. **Mỗi lượt đọc ghi một dòng audit.**

        Quyền ``rx.image.read`` (Chain chốt 2026-07-31), **không** phải ``rx.read``: thu
        ngân cần biết đơn có hợp lệ để bán hay không, không cần đọc chẩn đoán của khách.

        Ghi vết **trước khi** trả dữ liệu — nếu ghi sau, một lỗi ở giữa sẽ để lọt một lượt
        đọc không dấu vết, mà đó đúng là lượt đọc đáng ngờ nhất.
        """
        require_permission(ctx, "rx.image.read")
        rx = await self._get_or_404(prescription_id, ctx)
        if rx.image_data is None or rx.image_content_type is None:
            raise NotFoundError(f"Đơn thuốc {prescription_id} chưa có ảnh")
        await self._record(ctx, AuditAction.RX_IMAGE_VIEWED, rx.id)
        return PrescriptionImageOutput(
            prescription_id=rx.id,
            image_data=rx.image_data,
            content_type=rx.image_content_type,
        )

    async def _get_or_404(self, prescription_id: UUID, ctx: RequestContext) -> Prescription:
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            rx = await repo.get(prescription_id)
        if rx is None:
            raise NotFoundError(f"Không tìm thấy đơn thuốc {prescription_id}")
        return rx

    async def _record(
        self, ctx: RequestContext, action: AuditAction, prescription_id: UUID, **extra: str
    ) -> None:
        """Append one audit row — metadata only, never diagnosis/dosage content.

        ``extra`` chỉ nhận **siêu dữ liệu** (định dạng ảnh, số byte xấp xỉ), tuyệt đối
        không nhận nội dung: chép chẩn đoán hay chính ảnh vào sổ audit là biến nó thành
        bản sao thứ hai của dữ liệu nó đang canh (NĐ 356/2025 Điều 4.2).
        """
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=action,
                target_type="prescription",
                target_id=str(prescription_id),
            ).with_context(client_ip=ctx.client_ip, branch_id=str(ctx.branch_id), **extra)
        )
