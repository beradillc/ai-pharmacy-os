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

    async def _get_or_404(self, prescription_id: UUID, ctx: RequestContext) -> Prescription:
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            rx = await repo.get(prescription_id)
        if rx is None:
            raise NotFoundError(f"Không tìm thấy đơn thuốc {prescription_id}")
        return rx

    async def _record(
        self, ctx: RequestContext, action: AuditAction, prescription_id: UUID
    ) -> None:
        """Append one audit row — metadata only, never diagnosis/dosage content."""
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=action,
                target_type="prescription",
                target_id=str(prescription_id),
            ).with_context(client_ip=ctx.client_ip, branch_id=str(ctx.branch_id))
        )
