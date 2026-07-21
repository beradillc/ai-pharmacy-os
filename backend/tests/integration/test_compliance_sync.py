"""Integration tests for the national-DB sync flow — docs/13_COMPLIANCE_SPEC.md mục D.

Exercises the full loop with a stub gateway plus the real composition-root
``MockNationalDrugDbGateway``: enqueue -> send -> ACK/FAILED -> persist, idempotent by
client_uuid.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.api.v1.national_sync import MockNationalDrugDbGateway
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.modules.compliance.application import (
    NationalSyncService,
    PushSyncInput,
)
from pharmacy_os.modules.compliance.domain import (
    NationalDrugDbGateway,
    SyncAck,
    SyncPayloadType,
    SyncRequest,
    SyncStatus,
)
from pharmacy_os.modules.compliance.infrastructure import SqlAlchemyNationalSyncLogRepository


class _RejectingGateway:
    """Test double: always rejects, to drive the FAILED branch."""

    async def push(self, request: SyncRequest) -> SyncAck:
        return SyncAck(ok=False, response_code="503", response_body="unavailable")


class _RaisingGateway:
    """Test double: raises, to drive the exception -> FAILED branch."""

    async def push(self, request: SyncRequest) -> SyncAck:
        raise RuntimeError("connection refused")


def _service(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    gateway: NationalDrugDbGateway,
) -> NationalSyncService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    def repo_factory(uow: UnitOfWork, c: RequestContext) -> SqlAlchemyNationalSyncLogRepository:
        return SqlAlchemyNationalSyncLogRepository(uow.session, c)

    return NationalSyncService(uow_factory, repo_factory, gateway)


ServiceBuilder = Callable[[NationalDrugDbGateway], NationalSyncService]


@pytest.fixture
def build_sync_service(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> ServiceBuilder:
    def _build(gateway: NationalDrugDbGateway) -> NationalSyncService:
        return _service(session_factory, event_bus, gateway)

    return _build


def _payload(**kw: object) -> PushSyncInput:
    kw.setdefault("payload_type", SyncPayloadType.DRUG)
    kw.setdefault("client_uuid", "cli-001")
    kw.setdefault("payload", '{"ma_thuoc":"VD1234517lo200vien"}')
    return PushSyncInput(**kw)  # type: ignore[arg-type]


async def test_push_happy_path_reaches_ack_via_mock_adapter(
    build_sync_service: ServiceBuilder, ctx: RequestContext
) -> None:
    service = build_sync_service(MockNationalDrugDbGateway())
    out = await service.push_payload(_payload(), ctx)
    assert out.status == SyncStatus.ACK.value
    assert out.response_code is not None
    assert out.retry_count == 0
    assert out.payload_hash  # a hash was computed and stored


async def test_push_stores_only_hash_not_raw_payload(
    build_sync_service: ServiceBuilder, ctx: RequestContext
) -> None:
    service = build_sync_service(MockNationalDrugDbGateway())
    out = await service.push_payload(_payload(payload="SECRET-PAYLOAD"), ctx)
    # docs/13 mục D.2: the log carries payload_hash, never the raw payload.
    assert "SECRET-PAYLOAD" not in (out.payload_hash or "")
    assert not hasattr(out, "payload")


async def test_push_idempotent_replay_returns_existing_ack(
    build_sync_service: ServiceBuilder, ctx: RequestContext
) -> None:
    service = build_sync_service(MockNationalDrugDbGateway())
    first = await service.push_payload(_payload(client_uuid="cli-xyz"), ctx)
    second = await service.push_payload(_payload(client_uuid="cli-xyz"), ctx)
    assert first.id == second.id
    assert second.status == SyncStatus.ACK.value


async def test_push_rejected_gateway_records_failed(
    build_sync_service: ServiceBuilder, ctx: RequestContext
) -> None:
    service = build_sync_service(_RejectingGateway())
    out = await service.push_payload(_payload(), ctx)
    assert out.status == SyncStatus.FAILED.value
    assert out.retry_count == 1
    assert out.response_code == "503"


async def test_push_raising_gateway_records_failed(
    build_sync_service: ServiceBuilder, ctx: RequestContext
) -> None:
    service = build_sync_service(_RaisingGateway())
    out = await service.push_payload(_payload(), ctx)
    assert out.status == SyncStatus.FAILED.value
    assert out.retry_count == 1
    assert out.error is not None


async def test_failed_then_retry_succeeds_reuses_same_log(
    build_sync_service: ServiceBuilder, ctx: RequestContext
) -> None:
    failed = await build_sync_service(_RejectingGateway()).push_payload(
        _payload(client_uuid="cli-retry"), ctx
    )
    assert failed.status == SyncStatus.FAILED.value

    # A later attempt (gateway now healthy) reuses the same log row and ACKs it.
    retried = await build_sync_service(MockNationalDrugDbGateway()).push_payload(
        _payload(client_uuid="cli-retry"), ctx
    )
    assert retried.id == failed.id
    assert retried.status == SyncStatus.ACK.value
    assert retried.retry_count == 1  # the earlier failure is preserved


async def test_get_sync_log_by_id(build_sync_service: ServiceBuilder, ctx: RequestContext) -> None:
    service = build_sync_service(MockNationalDrugDbGateway())
    out = await service.push_payload(_payload(), ctx)
    fetched = await service.get_sync_log(out.id, ctx)
    assert fetched.id == out.id
    assert fetched.status == SyncStatus.ACK.value
