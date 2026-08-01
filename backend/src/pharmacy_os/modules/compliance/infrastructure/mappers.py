"""Mapping between compliance ORM rows and domain entities."""

from __future__ import annotations

from datetime import UTC, datetime

from pharmacy_os.modules.compliance.domain import (
    ControlledLedgerEntry,
    ControlledSubstanceCategory,
    CustomerDetail,
    DrugReturnRecord,
    LedgerBookSignature,
    LedgerBookType,
    LedgerDirection,
    NationalSyncLog,
    NationalSyncRetryTask,
    ReturnedDrugItem,
    SyncPayloadType,
    SyncRetryStatus,
    SyncStatus,
    TenantComplianceConfig,
)
from pharmacy_os.modules.compliance.infrastructure.models import (
    ControlledLedgerEntryORM,
    DrugReturnItemORM,
    DrugReturnRecordORM,
    LedgerBookSignatureORM,
    NationalSyncLogORM,
    NationalSyncRetryTaskORM,
    TenantComplianceConfigORM,
)


def ledger_entry_to_domain(row: ControlledLedgerEntryORM) -> ControlledLedgerEntry:
    customer = (
        CustomerDetail(patient_name=row.customer_name, patient_address=row.customer_address)
        if row.customer_name is not None and row.customer_address is not None
        else None
    )
    return ControlledLedgerEntry(
        id=row.id,
        tenant_id=row.tenant_id,
        branch_id=row.branch_id,
        drug_id=row.drug_id,
        category=ControlledSubstanceCategory(row.category),
        direction=LedgerDirection(row.direction),
        quantity=row.quantity,
        lot_no=row.lot_no,
        expiry_date=row.expiry_date,
        transaction_at=row.transaction_at,
        source_or_destination=row.source_or_destination,
        document_no=row.document_no,
        prescription_code=row.prescription_code,
        customer=customer,
        note=row.note,
        created_at=row.created_at,
    )


def ledger_entry_to_orm(entry: ControlledLedgerEntry) -> ControlledLedgerEntryORM:
    return ControlledLedgerEntryORM(
        id=entry.id,
        tenant_id=entry.tenant_id,
        branch_id=entry.branch_id,
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
        customer_name=entry.customer.patient_name if entry.customer is not None else None,
        customer_address=entry.customer.patient_address if entry.customer is not None else None,
        note=entry.note,
        created_at=entry.created_at,
    )


def tenant_config_to_domain(row: TenantComplianceConfigORM) -> TenantComplianceConfig:
    return TenantComplianceConfig(
        id=row.id,
        tenant_id=row.tenant_id,
        ma_co_so_ban_le=row.ma_co_so_ban_le,
        ma_co_so_ban_buon=row.ma_co_so_ban_buon,
        ten_co_so=row.ten_co_so,
        dia_chi=row.dia_chi,
        dien_thoai=row.dien_thoai,
        ma_so_thue=row.ma_so_thue,
    )


def tenant_config_to_orm(config: TenantComplianceConfig) -> TenantComplianceConfigORM:
    return TenantComplianceConfigORM(
        id=config.id,
        tenant_id=config.tenant_id,
        ma_co_so_ban_le=config.ma_co_so_ban_le,
        ma_co_so_ban_buon=config.ma_co_so_ban_buon,
        ten_co_so=config.ten_co_so,
        dia_chi=config.dia_chi,
        dien_thoai=config.dien_thoai,
        ma_so_thue=config.ma_so_thue,
    )


def sync_log_to_domain(row: NationalSyncLogORM) -> NationalSyncLog:
    return NationalSyncLog(
        id=row.id,
        tenant_id=row.tenant_id,
        payload_type=SyncPayloadType(row.payload_type),
        payload_hash=row.payload_hash,
        client_uuid=row.client_uuid,
        status=SyncStatus(row.status),
        request_at=row.request_at,
        response_at=row.response_at,
        response_code=row.response_code,
        response_body=row.response_body,
        retry_count=row.retry_count,
        error=row.error,
        created_at=row.created_at,
    )


def sync_log_to_orm(log: NationalSyncLog) -> NationalSyncLogORM:
    return NationalSyncLogORM(
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
        created_at=log.created_at,
    )


def _as_utc(value: datetime) -> datetime:
    """SQLite drops the tz that ``DateTime(timezone=True)`` keeps on Postgres; everything is
    written in UTC, so re-attaching it restates the value rather than changing it. Only the
    retry queue needs this: its timestamps are compared against ``now`` in Python."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def sync_retry_task_to_domain(row: NationalSyncRetryTaskORM) -> NationalSyncRetryTask:
    return NationalSyncRetryTask(
        id=row.id,
        tenant_id=row.tenant_id,
        branch_id=row.branch_id,
        sync_log_id=row.sync_log_id,
        payload_type=SyncPayloadType(row.payload_type),
        client_uuid=row.client_uuid,
        payload=row.payload,
        status=SyncRetryStatus(row.status),
        attempt_count=row.attempt_count,
        next_attempt_at=_as_utc(row.next_attempt_at) if row.next_attempt_at else None,
        last_error=row.last_error,
        created_at=_as_utc(row.created_at),
    )


def sync_retry_task_to_orm(task: NationalSyncRetryTask) -> NationalSyncRetryTaskORM:
    return NationalSyncRetryTaskORM(
        id=task.id,
        tenant_id=task.tenant_id,
        branch_id=task.branch_id,
        sync_log_id=task.sync_log_id,
        payload_type=task.payload_type.value,
        client_uuid=task.client_uuid,
        payload=task.payload,
        status=task.status.value,
        attempt_count=task.attempt_count,
        next_attempt_at=task.next_attempt_at,
        last_error=task.last_error,
        created_at=task.created_at,
    )


def ledger_book_signature_to_domain(row: LedgerBookSignatureORM) -> LedgerBookSignature:
    return LedgerBookSignature(
        id=row.id,
        tenant_id=row.tenant_id,
        book_type=LedgerBookType(row.book_type),
        book_date=row.book_date,
        content_sha256=row.content_sha256,
        prev_hash=row.prev_hash,
        signed_by_user_id=row.signed_by_user_id,
        signed_at=row.signed_at,
    )


def ledger_book_signature_to_orm(signature: LedgerBookSignature) -> LedgerBookSignatureORM:
    return LedgerBookSignatureORM(
        id=signature.id,
        tenant_id=signature.tenant_id,
        book_type=signature.book_type.value,
        book_date=signature.book_date,
        content_sha256=signature.content_sha256,
        prev_hash=signature.prev_hash,
        signed_by_user_id=signature.signed_by_user_id,
        signed_at=signature.signed_at,
    )


def drug_return_record_to_domain(row: DrugReturnRecordORM) -> DrugReturnRecord:
    return DrugReturnRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        branch_id=row.branch_id,
        returner_name=row.returner_name,
        returner_address=row.returner_address,
        returner_id_number=row.returner_id_number,
        returner_id_issuer=row.returner_id_issuer,
        returner_id_issued_at=row.returner_id_issued_at,
        returner_is_patient=row.returner_is_patient,
        receiving_pharmacist_name=row.receiving_pharmacist_name,
        items=[
            ReturnedDrugItem(
                description=i.description,
                unit=i.unit,
                quantity=i.quantity,
                lot_no=i.lot_no,
                expiry_date=i.expiry_date,
                condition_note=i.condition_note,
                reason=i.reason,
            )
            for i in row.items
        ],
        handover_at=row.handover_at,
        handover_location=row.handover_location,
        created_at=row.created_at,
    )


def drug_return_record_to_orm(record: DrugReturnRecord) -> DrugReturnRecordORM:
    return DrugReturnRecordORM(
        id=record.id,
        tenant_id=record.tenant_id,
        branch_id=record.branch_id,
        returner_name=record.returner_name,
        returner_address=record.returner_address,
        returner_id_number=record.returner_id_number,
        returner_id_issuer=record.returner_id_issuer,
        returner_id_issued_at=record.returner_id_issued_at,
        returner_is_patient=record.returner_is_patient,
        receiving_pharmacist_name=record.receiving_pharmacist_name,
        handover_at=record.handover_at,
        handover_location=record.handover_location,
        items=[
            DrugReturnItemORM(
                record_id=record.id,
                description=i.description,
                unit=i.unit,
                quantity=i.quantity,
                lot_no=i.lot_no,
                expiry_date=i.expiry_date,
                condition_note=i.condition_note,
                reason=i.reason,
            )
            for i in record.items
        ],
    )
