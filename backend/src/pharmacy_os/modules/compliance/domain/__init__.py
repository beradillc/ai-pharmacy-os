"""Compliance domain: national drug record, controlled-substance ledger, converter
helpers for QĐ540/TT20/2017 legal-compliance sync. Framework-free.
"""

from pharmacy_os.modules.compliance.domain.converters import (
    to_qld_code,
    to_qld_date,
    to_qld_datetime,
)
from pharmacy_os.modules.compliance.domain.entities import (
    ControlledLedgerEntry,
    ControlledSubstanceCategory,
    CustomerDetail,
    LedgerDirection,
    NationalDrugRecord,
    TenantComplianceConfig,
)
from pharmacy_os.modules.compliance.domain.exceptions import (
    ComplianceError,
    MissingControlledCustomerDetailError,
    MissingControlledPrescriptionCodeError,
    MissingEtcPrescriptionFieldsError,
    NotControlledSubstanceError,
)
from pharmacy_os.modules.compliance.domain.ports import (
    ControlledLedgerRepository,
    DrugMasterFacts,
    DrugMasterProvider,
    TenantComplianceConfigRepository,
)
from pharmacy_os.modules.compliance.domain.rules import (
    EtcPrescriptionPolicy,
    validate_controlled_sale,
    validate_etc_sale,
)

__all__ = [
    "to_qld_code",
    "to_qld_date",
    "to_qld_datetime",
    "ControlledLedgerEntry",
    "ControlledSubstanceCategory",
    "CustomerDetail",
    "LedgerDirection",
    "NationalDrugRecord",
    "TenantComplianceConfig",
    "ComplianceError",
    "MissingControlledCustomerDetailError",
    "MissingControlledPrescriptionCodeError",
    "MissingEtcPrescriptionFieldsError",
    "NotControlledSubstanceError",
    "ControlledLedgerRepository",
    "DrugMasterFacts",
    "DrugMasterProvider",
    "TenantComplianceConfigRepository",
    "EtcPrescriptionPolicy",
    "validate_controlled_sale",
    "validate_etc_sale",
]
