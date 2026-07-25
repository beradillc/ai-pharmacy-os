"""Gửi lại tự động các bản ghi liên thông CSDL Dược đang treo (docs/13 mục D.4).

**Vá đúng lỗ hổng nào.** ``NationalSyncService.push_payload`` là *best-effort*: cổng từ
chối thì dòng ``NationalSyncLog`` chuyển ``FAILED`` và dừng ở đó — cho tới nay phải có
người POST lại thủ công đúng payload cũ thì bản ghi mới đi tiếp. Với QĐ1867 mục I.2
("cập nhật, đồng bộ... **kịp thời**") thì "chờ ai đó nhớ ra" không phải một cơ chế. Relay
này là cơ chế đó: quét việc tới hạn, gọi lại chính ``push_payload``, có giãn cách và có
điểm dừng.

**Vì sao không dùng thẳng outbox lõi.** ``core.outbox`` giao *sự kiện nội bộ tới event
bus*; theo đúng docstring của :mod:`pharmacy_os.core.outbox.relay`, subscriber hỏng là
được nuốt và ghi log, **không** retry — retry của nó chỉ phủ khâu đưa lên bus. Việc ở đây
là khâu sau: một cuộc gọi ra **cổng ngoài** (CSDL Dược) có thể hỏng hàng giờ. Hai mối lo
khác nhau, nên đây là một relay riêng **mô phỏng hình dáng** OutboxRelay (claim ``FOR
UPDATE SKIP LOCKED`` → backoff → hết lượt thì dừng → có cờ bật/tắt → gắn vào lifespan
app) chứ không phải một đường "publish" thứ hai — chưa từng có đường publish nào thứ nhất
cho cổng DAV để mà trùng.

**Khác OutboxRelay một điểm có chủ đích:** relay này **không** giữ transaction CSDL trong
lúc gọi cổng. Nó nhận việc + đặt lease trong 1 transaction ngắn, gọi mạng ở ngoài, rồi
ghi kết quả trong transaction thứ hai. Bus nội bộ nhanh nên OutboxRelay giữ nguyên 1
transaction là chấp nhận được; một cuộc gọi HTTP ra ngoài (khi có adapter thật) thì
không. Đổi lại là at-least-once — an toàn, vì ``push_payload`` idempotent theo
``client_uuid`` và bản ghi đã ``ACK`` được trả nguyên trạng, không gửi lại.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

import structlog

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.modules.compliance.application.dto import (
    NationalSyncLogOutput,
    PushSyncInput,
)
from pharmacy_os.modules.compliance.domain import (
    NationalSyncRetryClaimer,
    NationalSyncRetryTask,
    SyncStatus,
)

_log = structlog.get_logger("compliance.national_sync.retry")

UowFactory = Callable[[], UnitOfWork]
ClaimerFactory = Callable[[UnitOfWork], NationalSyncRetryClaimer]
Clock = Callable[[], datetime]

SYNC_SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-00005a1e5c05")
"""Danh tính hệ thống cho mọi lần đẩy không do người dùng bấm.

Đặt ở tầng application (không phải composition root) vì nay có **hai** chỗ đẩy tự động —
subscriber ``SaleCompleted`` và relay này — và hai chỗ đó phải là *cùng một* actor trong
mọi vết log/audit, không phải hai UUID hằng số chép tay giống nhau tình cờ.
"""

SYNC_SYSTEM_PERMISSIONS = frozenset({"compliance.sync.push"})
"""Đúng một quyền cần dùng — không phải bộ quyền đầy đủ."""


@dataclass(frozen=True, slots=True)
class SyncRetryConfig:
    batch_size: int = 20
    """Nhỏ hơn outbox (100) có chủ đích: mỗi việc là một cuộc gọi mạng ra ngoài, không
    phải một lần dispatch trong tiến trình."""

    max_retries: int = 8
    base_backoff_seconds: float = 60.0
    """60s × 2^(n-1) trong 8 lượt ≈ 4 giờ rưỡi rồi mới bỏ cuộc — đủ để cổng quốc gia bảo
    trì xong mà không gõ cửa liên tục."""

    lease_seconds: float = 300.0
    """Việc đã nhận bị giấu đi bấy nhiêu lâu. Phải dài hơn thời gian một lần gọi cổng xấu
    nhất, nếu không hai vòng quét sẽ cùng đẩy một bản ghi (vô hại nhờ idempotency, nhưng
    tốn công vô ích)."""


@dataclass(frozen=True, slots=True)
class SyncRetryResult:
    """Kết quả một lượt :meth:`NationalSyncRetryRelay.drain_once`."""

    acked: int = 0
    retried: int = 0
    dead: int = 0

    @property
    def processed(self) -> int:
        return self.acked + self.retried + self.dead


class SyncPusher(Protocol):
    """Phần ``NationalSyncService`` mà relay cần — chỉ đúng 1 phương thức."""

    async def push_payload(
        self, data: PushSyncInput, ctx: RequestContext
    ) -> NationalSyncLogOutput: ...


def _default_clock() -> datetime:
    return datetime.now(UTC)


class NationalSyncRetryRelay:
    def __init__(
        self,
        uow_factory: UowFactory,
        claimer_factory: ClaimerFactory,
        pusher: SyncPusher,
        config: SyncRetryConfig | None = None,
        clock: Clock = _default_clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._claimer_factory = claimer_factory
        self._pusher = pusher
        self._config = config or SyncRetryConfig()
        self._now = clock

    async def drain_once(self) -> SyncRetryResult:
        """Nhận một mẻ việc tới hạn, đẩy lại từng việc, ghi kết quả."""
        tasks = await self._claim_batch()
        acked = retried = dead = 0
        for task in tasks:
            outcome = await self._attempt(task)
            if outcome is None:
                acked += 1
            elif outcome:
                retried += 1
            else:
                dead += 1
        result = SyncRetryResult(acked=acked, retried=retried, dead=dead)
        if result.processed:
            _log.info("national_sync_retry_drained", acked=acked, retried=retried, dead=dead)
        return result

    async def run_forever(self, poll_interval_seconds: float) -> None:
        """Quét theo vòng cho tới khi bị hủy — task nền của app.

        Một lượt quét nổ (CSDL sập chẳng hạn) không được giết vòng lặp: ghi log rồi thử
        lại nhịp sau, vì việc vẫn còn nguyên trong bảng. Chỉ hủy task mới thoát được, và
        hủy phải lan ra ngoài để lúc tắt app không bị chờ.
        """
        while True:
            try:
                await self.drain_once()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 — một lượt hỏng không được dừng vòng quét
                _log.exception("national_sync_retry_drain_failed")
            await asyncio.sleep(poll_interval_seconds)

    async def _claim_batch(self) -> list[NationalSyncRetryTask]:
        now = self._now()
        lease_until = now + timedelta(seconds=self._config.lease_seconds)
        async with self._uow_factory() as uow:
            claimer = self._claimer_factory(uow)
            tasks = await claimer.claim_due(
                now, limit=self._config.batch_size, lease_until=lease_until
            )
            await uow.commit()
        return tasks

    async def _attempt(self, task: NationalSyncRetryTask) -> bool | None:
        """Đẩy lại 1 việc. ``None`` = đã ACK (xóa việc), ``True`` = hẹn lại, ``False`` = DEAD."""
        ctx = RequestContext(
            tenant_id=task.tenant_id,
            branch_id=task.branch_id,
            user_id=SYNC_SYSTEM_USER_ID,
            permissions=SYNC_SYSTEM_PERMISSIONS,
        )
        try:
            output = await self._pusher.push_payload(
                PushSyncInput(
                    payload_type=task.payload_type,
                    client_uuid=task.client_uuid,
                    payload=task.payload,
                ),
                ctx,
            )
        except Exception as exc:  # noqa: BLE001 — mọi lỗi thành 1 lần thử hỏng, không nổ vòng quét
            error = repr(exc)
        else:
            if output.status == SyncStatus.ACK.value:
                await self._complete(task)
                return None
            error = output.error or f"cổng trả trạng thái {output.status}"
        return await self._record_failure(task, error)

    async def _complete(self, task: NationalSyncRetryTask) -> None:
        """Đã ACK: xóa việc — payload hết lý do tồn tại ngay tại đây (mục D.4).

        ``push_payload`` cũng đã tự dọn trong transaction của nó; gọi lại ở đây là chốt
        chặn thứ hai, xóa dòng không tồn tại là no-op nên vô hại.
        """
        async with self._uow_factory() as uow:
            await self._claimer_factory(uow).delete(task.id)
            await uow.commit()
        _log.info(
            "national_sync_retry_acked",
            client_uuid=task.client_uuid,
            payload_type=task.payload_type.value,
            attempts=task.attempt_count + 1,
        )

    async def _record_failure(self, task: NationalSyncRetryTask, error: str) -> bool:
        alive = task.record_failure(
            error=error,
            now=self._now(),
            base_backoff_seconds=self._config.base_backoff_seconds,
            max_retries=self._config.max_retries,
        )
        async with self._uow_factory() as uow:
            await self._claimer_factory(uow).save(task)
            await uow.commit()
        if alive:
            _log.warning(
                "national_sync_retry_scheduled",
                client_uuid=task.client_uuid,
                attempt_count=task.attempt_count,
                next_attempt_at=task.next_attempt_at,
                error=error,
            )
        else:
            _log.error(
                "national_sync_retry_dead_lettered",
                client_uuid=task.client_uuid,
                payload_type=task.payload_type.value,
                attempt_count=task.attempt_count,
                error=error,
                detail=("hết lượt thử tự động — bản ghi CHƯA lên được CSDL Dược, cần người xử lý"),
            )
        return alive
