"""Compliance ports: persistence (implemented by infrastructure) and cross-module
read access (implemented at the composition root, same pattern as
``sales.DrugInfoProvider`` / ``CatalogDrugInfoProvider`` — ``compliance`` never imports
catalog/inventory/sales/prescription directly).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.compliance.domain.entities import (
    ControlledLedgerEntry,
    TenantComplianceConfig,
)


class ControlledLedgerRepository(Protocol):
    """Persistence port for :class:`ControlledLedgerEntry` (immutable — add/get only)."""

    async def add(self, entry: ControlledLedgerEntry) -> None: ...

    async def get(self, entry_id: UUID) -> ControlledLedgerEntry | None: ...


class TenantComplianceConfigRepository(Protocol):
    """Persistence port for :class:`TenantComplianceConfig` (one row per tenant)."""

    async def upsert(self, config: TenantComplianceConfig) -> None: ...

    async def get(self, tenant_id: UUID) -> TenantComplianceConfig | None: ...


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
