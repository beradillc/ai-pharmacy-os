"""Compliance ports: persistence (implemented by infrastructure) and cross-module
read access (implemented at the composition root, same pattern as
``sales.DrugInfoProvider`` / ``CatalogDrugInfoProvider`` — ``compliance`` never imports
catalog/inventory/sales/prescription directly).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.compliance.domain.entities import (
    ControlledLedgerEntry,
    LedgerBookType,
    NationalSyncLog,
    SyncPayloadType,
    TenantComplianceConfig,
)


class ControlledLedgerRepository(Protocol):
    """Persistence port for :class:`ControlledLedgerEntry` (immutable — add/get/list only)."""

    async def add(self, entry: ControlledLedgerEntry) -> None: ...

    async def get(self, entry_id: UUID) -> ControlledLedgerEntry | None: ...

    async def list_for_book(
        self,
        book_type: LedgerBookType,
        *,
        from_date: date,
        to_date: date,
        drug_id: UUID | None = None,
    ) -> Sequence[ControlledLedgerEntry]:
        """Các dòng thuộc một mẫu sổ trong kỳ, sắp xếp theo (thuốc, thời điểm giao dịch).

        Sắp theo thuốc trước vì mẫu sổ pháp lý yêu cầu **mỗi thuốc một sổ riêng**
        (ghi chú Phụ lục VIII), và cột "Còn lại" là tồn lũy kế trong phạm vi từng thuốc.
        """
        ...


class TenantComplianceConfigRepository(Protocol):
    """Persistence port for :class:`TenantComplianceConfig` (one row per tenant)."""

    async def upsert(self, config: TenantComplianceConfig) -> None: ...

    async def get(self, tenant_id: UUID) -> TenantComplianceConfig | None: ...


class NationalSyncLogRepository(Protocol):
    """Persistence port for :class:`NationalSyncLog` (tenant-scoped)."""

    async def add(self, log: NationalSyncLog) -> None: ...

    async def update(self, log: NationalSyncLog) -> None: ...

    async def get(self, log_id: UUID) -> NationalSyncLog | None: ...

    async def by_client_uuid(self, client_uuid: str) -> NationalSyncLog | None: ...


@dataclass(frozen=True, slots=True)
class SyncRequest:
    """A single record/batch to push to the national drug database (docs/13 mục D.2)."""

    payload_type: SyncPayloadType
    client_uuid: str
    payload: str  # serialized payload sent to the gateway; only its hash is persisted


@dataclass(frozen=True, slots=True)
class SyncAck:
    """The gateway's response to a push. ``ok`` distinguishes ACK from FAILED."""

    ok: bool
    response_code: str | None
    response_body: str | None


class NationalDrugDbGateway(Protocol):
    """Outbound port to the CSDL Dược Quốc gia (docs/13 mục D.3).

    ⚠️ The real endpoint spec does not exist yet (due ~6/2026 per QĐ1867 mục 1.2). Only a
    ``MockNationalDrugDbGateway`` implements this today, wired at the composition root — the
    real adapter is deliberately not built until the DAV API spec is available.
    """

    async def push(self, request: SyncRequest) -> SyncAck: ...


@dataclass(frozen=True, slots=True)
class DrugMasterFacts:
    """Catalog facts compliance needs to build a ``NationalDrugRecord`` (docs/13 mục B)."""

    registration_no: str | None
    base_unit: str


class DrugMasterProvider(Protocol):
    """Read-port for catalog facts (docs/13 mục B mapping `so_dang_ky`/`don_vi_dong_goi_nn`).

    Returns ``None`` when the drug is unknown to catalog.
    """

    async def get(self, drug_id: UUID, tenant_id: UUID) -> DrugMasterFacts | None: ...
