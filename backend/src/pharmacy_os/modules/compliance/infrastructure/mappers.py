"""Mapping between compliance ORM rows and domain entities."""

from __future__ import annotations

from pharmacy_os.modules.compliance.domain import (
    ControlledLedgerEntry,
    ControlledSubstanceCategory,
    CustomerDetail,
    LedgerDirection,
    TenantComplianceConfig,
)
from pharmacy_os.modules.compliance.infrastructure.models import (
    ControlledLedgerEntryORM,
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
    )


def tenant_config_to_orm(config: TenantComplianceConfig) -> TenantComplianceConfigORM:
    return TenantComplianceConfigORM(
        id=config.id,
        tenant_id=config.tenant_id,
        ma_co_so_ban_le=config.ma_co_so_ban_le,
        ma_co_so_ban_buon=config.ma_co_so_ban_buon,
    )
