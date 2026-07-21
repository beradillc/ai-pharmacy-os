"""National-DB sync use-case (docs/13_COMPLIANCE_SPEC.md mục D).

Drives one payload through the audited push loop: create/reuse a :class:`NationalSyncLog`
(idempotent by ``client_uuid``), send it via the injected :class:`NationalDrugDbGateway`, and
record the outcome (ACK/FAILED). Sync is best-effort: a gateway rejection or error is recorded
on the log (FAILED, ``retry_count`` bumped) rather than raised, so an upstream event handler
(C.5) never crashes on a sync hiccup — a later attempt reuses the same log and can ACK it.

Depends only on ports; the concrete repository, unit of work and gateway are injected at
composition time. The gateway is a ``MockNationalDrugDbGateway`` today — no real endpoint is
wired until the DAV API spec exists (docs/13 mục D.3).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from uuid import UUID

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import NotFoundError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.compliance.application.dto import (
    NationalSyncLogOutput,
    PushSyncInput,
)
from pharmacy_os.modules.compliance.domain import (
    NationalDrugDbGateway,
    NationalSyncLog,
    SyncAck,
    SyncRequest,
    SyncStatus,
)
from pharmacy_os.modules.compliance.domain.ports import NationalSyncLogRepository

UowFactory = Callable[[], UnitOfWork]
SyncLogRepoFactory = Callable[[UnitOfWork, RequestContext], NationalSyncLogRepository]


class NationalSyncService:
    def __init__(
        self,
        uow_factory: UowFactory,
        sync_log_repo_factory: SyncLogRepoFactory,
        gateway: NationalDrugDbGateway,
    ) -> None:
        self._uow_factory = uow_factory
        self._sync_log_repo_factory = sync_log_repo_factory
        self._gateway = gateway

    async def push_payload(self, data: PushSyncInput, ctx: RequestContext) -> NationalSyncLogOutput:
        """Đẩy 1 bản ghi lên CSDL Dược, idempotent theo ``client_uuid``.

        Bản ghi đã ``ACK`` trước đó → trả nguyên trạng (không gửi lại). Bản ghi cũ ``PENDING``/
        ``FAILED`` → gửi lại trên cùng dòng log. Chưa có → tạo dòng ``PENDING`` mới.
        """
        require_permission(ctx, "compliance.sync.push")
        payload_hash = hashlib.sha256(data.payload.encode("utf-8")).hexdigest()

        # Step 1: get-or-create the log (persisted PENDING), idempotent by client_uuid.
        async with self._uow_factory() as uow:
            repo = self._sync_log_repo_factory(uow, ctx)
            existing = await repo.by_client_uuid(data.client_uuid)
            if existing is not None:
                if existing.status is SyncStatus.ACK:
                    return NationalSyncLogOutput.of(existing)  # already synced — no re-push
                log = existing  # reuse the row for a retry
            else:
                log = NationalSyncLog(
                    tenant_id=ctx.tenant_id,
                    payload_type=data.payload_type,
                    payload_hash=payload_hash,
                    client_uuid=data.client_uuid,
                )
                await repo.add(log)
            await uow.commit()

        # Step 2: send to the gateway (external I/O — outside the DB transaction).
        log.mark_sent()
        try:
            ack = await self._gateway.push(
                SyncRequest(
                    payload_type=data.payload_type,
                    client_uuid=data.client_uuid,
                    payload=data.payload,
                )
            )
        except Exception as exc:  # gateway unreachable/raised — record, don't crash caller
            log.mark_failed(error=f"Gateway error: {exc}")
        else:
            self._apply_ack(log, ack)

        # Step 3: persist the outcome.
        async with self._uow_factory() as uow:
            repo = self._sync_log_repo_factory(uow, ctx)
            await repo.update(log)
            await uow.commit()

        return NationalSyncLogOutput.of(log)

    @staticmethod
    def _apply_ack(log: NationalSyncLog, ack: SyncAck) -> None:
        if ack.ok:
            log.mark_acked(response_code=ack.response_code, response_body=ack.response_body)
        else:
            log.mark_failed(
                error=f"Cổng CSDL Dược từ chối (code={ack.response_code})",
                response_code=ack.response_code,
            )

    async def get_sync_log(self, log_id: UUID, ctx: RequestContext) -> NationalSyncLogOutput:
        """Trả về 1 dòng audit truyền nhận theo id, đã tenant-scope; 404 nếu không có."""
        require_permission(ctx, "compliance.sync.read")
        async with self._uow_factory() as uow:
            repo = self._sync_log_repo_factory(uow, ctx)
            log = await repo.get(log_id)
        if log is None:
            raise NotFoundError(f"Không tìm thấy dòng đồng bộ CSDL Dược {log_id}")
        return NationalSyncLogOutput.of(log)
