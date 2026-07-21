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
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.di import Container
from pharmacy_os.core.events import EventBus
from pharmacy_os.modules.compliance.application import NationalSyncService
from pharmacy_os.modules.compliance.domain import SyncAck, SyncRequest
from pharmacy_os.modules.compliance.infrastructure import SqlAlchemyNationalSyncLogRepository

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
    """Register ``NationalSyncService`` backed by the mock gateway.

    A side-effect wiring (no router) — the service is resolvable for the cross-module
    subscriber added in C.5, which will enqueue sync pushes off business events.
    """
    session_factory = container.resolve(async_sessionmaker[AsyncSession])
    event_bus = container.resolve(EventBus)  # type: ignore[type-abstract]

    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    def repo_factory(uow: UnitOfWork, ctx: RequestContext) -> SqlAlchemyNationalSyncLogRepository:
        return SqlAlchemyNationalSyncLogRepository(uow.session, ctx)

    service = NationalSyncService(uow_factory, repo_factory, MockNationalDrugDbGateway())
    container.register_instance(NationalSyncService, service)
