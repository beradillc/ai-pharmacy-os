"""Compliance data-transfer objects (framework-free dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pharmacy_os.modules.compliance.domain import (
    ControlledLedgerEntry,
    ControlledSubstanceCategory,
    LedgerDirection,
    NationalSyncLog,
    SyncPayloadType,
    TenantComplianceConfig,
)


@dataclass(slots=True)
class CustomerDetailInput:
    patient_name: str
    patient_address: str


@dataclass(slots=True)
class RecordControlledEntryInput:
    drug_id: UUID
    category: ControlledSubstanceCategory
    direction: LedgerDirection
    quantity: Decimal
    lot_no: str
    expiry_date: date
    transaction_at: datetime
    source_or_destination: str
    document_no: str
    prescription_code: str | None = None
    customer: CustomerDetailInput | None = None
    note: str | None = None


@dataclass(slots=True)
class CustomerDetailOutput:
    patient_name: str
    patient_address: str


@dataclass(slots=True)
class ControlledLedgerEntryOutput:
    id: UUID
    drug_id: UUID
    category: str
    direction: str
    quantity: Decimal
    lot_no: str
    expiry_date: date
    transaction_at: datetime
    source_or_destination: str
    document_no: str
    prescription_code: str | None
    customer: CustomerDetailOutput | None
    note: str | None

    @classmethod
    def of(cls, entry: ControlledLedgerEntry) -> ControlledLedgerEntryOutput:
        return cls(
            id=entry.id,
            drug_id=entry.drug_id,
            category=entry.category.value,
            direction=entry.direction.value,
            quantity=entry.quantity,
            lot_no=entry.lot_no,
            expiry_date=entry.expiry_date,
            transaction_at=entry.transaction_at,
            source_or_destination=entry.source_or_destination,
            document_no=entry.document_no,
            prescription_code=entry.prescription_code,
            customer=(
                CustomerDetailOutput(
                    patient_name=entry.customer.patient_name,
                    patient_address=entry.customer.patient_address,
                )
                if entry.customer is not None
                else None
            ),
            note=entry.note,
        )


@dataclass(slots=True)
class SetTenantComplianceConfigInput:
    ma_co_so_ban_le: str
    ma_co_so_ban_buon: str | None = None


@dataclass(slots=True)
class TenantComplianceConfigOutput:
    tenant_id: UUID
    ma_co_so_ban_le: str
    ma_co_so_ban_buon: str | None

    @classmethod
    def of(cls, config: TenantComplianceConfig) -> TenantComplianceConfigOutput:
        return cls(
            tenant_id=config.tenant_id,
            ma_co_so_ban_le=config.ma_co_so_ban_le,
            ma_co_so_ban_buon=config.ma_co_so_ban_buon,
        )


@dataclass(slots=True)
class PushSyncInput:
    """A record/batch to push to the national drug database (docs/13 mục D).

    ``payload`` is the serialized data sent to the gateway; the log stores only its hash.
    """

    payload_type: SyncPayloadType
    client_uuid: str
    payload: str


@dataclass(slots=True)
class NationalSyncLogOutput:
    id: UUID
    tenant_id: UUID
    payload_type: str
    payload_hash: str
    client_uuid: str
    status: str
    request_at: datetime
    response_at: datetime | None
    response_code: str | None
    response_body: str | None
    retry_count: int
    error: str | None

    @classmethod
    def of(cls, log: NationalSyncLog) -> NationalSyncLogOutput:
        return cls(
            id=log.id,
            tenant_id=log.tenant_id,
            payload_type=log.payload_type.value,
            payload_hash=log.payload_hash,
            client_uuid=log.client_uuid,
            status=log.status.value,
            request_at=log.request_at,
            response_at=log.response_at,
            response_code=log.response_code,
            response_body=log.response_body,
            retry_count=log.retry_count,
            error=log.error,
        )
