"""Composition-root wiring for national drug database sync (docs/13 mục D).

The outbound port ``NationalDrugDbGateway`` lives in the compliance domain; its only
implementation today is the mock below. The real adapter is deliberately NOT built:

    # BLOCKER: DAV API spec

The endpoint specification (Trung tâm Thông tin y tế Quốc gia, due ~6/2026 per QĐ 1867
mục 1.2) does not exist yet. When it arrives, add a real ``NationalDrugDbGateway`` adapter
here and swap it into ``wire_national_sync`` — nothing in the domain/application layers
changes, because they depend only on the port.
"""

from __future__ import annotations

import structlog

from pharmacy_os.core.bootstrap import refuse_mock_in_prod
from pharmacy_os.core.config import Settings
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork, UnitOfWorkFactory
from pharmacy_os.core.di import Container
from pharmacy_os.modules.compliance.application import (
    NationalSyncRetryRelay,
    NationalSyncService,
    SyncRetryConfig,
)
from pharmacy_os.modules.compliance.domain import SyncAck, SyncRequest
from pharmacy_os.modules.compliance.infrastructure import (
    SqlAlchemyNationalSyncLogRepository,
    SqlAlchemyNationalSyncRetryClaimer,
    SqlAlchemyNationalSyncRetryQueue,
)

_log = structlog.get_logger("compliance.national_sync")


class MockNationalDrugDbGateway:
    """Stand-in for the CSDL Dược Quốc gia gateway — logs and returns a fake ACK.

    # BLOCKER: DAV API spec — no real HTTP call is made. This exists only so the full sync
    loop (create log → send → ACK → persist) can be exercised end-to-end until the real
    endpoint specification is published.
    """

    async def push(self, request: SyncRequest) -> SyncAck:
        _log.info(
            "national_sync_mock_push",
            payload_type=request.payload_type.value,
            client_uuid=request.client_uuid,
            note="MOCK — no real DAV endpoint (BLOCKER: DAV API spec)",
        )
        return SyncAck(ok=True, response_code="200", response_body='{"ack":true,"mock":true}')


def wire_national_sync(container: Container) -> None:
    """Register ``NationalSyncService`` + the retry relay, both on the mock gateway.

    A side-effect wiring (no router) — the service is resolvable for the cross-module
    subscriber added in C.5, which will enqueue sync pushes off business events.

    Chỉ **đăng ký** relay ở đây; ai *chạy* nó là lifespan của app (``main._lifespan``) khi
    ``NATIONAL_SYNC__RETRY_ENABLED`` bật — một bộ quét nền phải gắn vào vòng đời tiến
    trình, không phải vào lúc dựng router. Đúng khuôn ``wire_outbox`` đang dùng.
    """
    uow_factory = container.resolve(UnitOfWorkFactory)
    settings = container.resolve(Settings)

    def repo_factory(uow: UnitOfWork, ctx: RequestContext) -> SqlAlchemyNationalSyncLogRepository:
        return SqlAlchemyNationalSyncLogRepository(uow.session, ctx)

    def retry_queue(uow: UnitOfWork, ctx: RequestContext) -> SqlAlchemyNationalSyncRetryQueue:
        return SqlAlchemyNationalSyncRetryQueue(uow.session, ctx)

    def retry_claimer(uow: UnitOfWork) -> SqlAlchemyNationalSyncRetryClaimer:
        return SqlAlchemyNationalSyncRetryClaimer(uow.session)

    refuse_mock_in_prod(
        settings,
        "MockNationalDrugDbGateway",
        "liên thông CSDL Dược Quốc gia (QĐ1867) — ACK giả nghĩa là báo cáo coi như đã gửi",
    )
    service = NationalSyncService(
        uow_factory, repo_factory, MockNationalDrugDbGateway(), retry_queue
    )
    container.register_instance(NationalSyncService, service)

    relay = NationalSyncRetryRelay(
        uow_factory,
        retry_claimer,
        service,
        SyncRetryConfig(
            batch_size=settings.national_sync.batch_size,
            max_retries=settings.national_sync.max_retries,
            base_backoff_seconds=settings.national_sync.base_backoff_seconds,
            lease_seconds=settings.national_sync.lease_seconds,
        ),
    )
    container.register_instance(NationalSyncRetryRelay, relay)

    if settings.app.env == "prod" and not settings.national_sync.retry_enabled:
        _log.warning(
            "national_sync_retry_disabled_in_prod",
            detail=(
                "bản ghi bị cổng CSDL Dược từ chối sẽ nằm trong hàng đợi tới khi có người "
                "POST lại tay — đặt NATIONAL_SYNC__RETRY_ENABLED=true"
            ),
        )
