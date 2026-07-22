"""CRM domain: customer/patient master data. Framework-free."""

from pharmacy_os.modules.crm.domain.entities import (
    Allergy,
    AllergySeverity,
    Condition,
    Customer,
    MedicationHistoryEntry,
    MedicationHistorySource,
)
from pharmacy_os.modules.crm.domain.exceptions import (
    CrmError,
    DuplicateAllergyError,
    DuplicateConditionError,
    InvalidConditionError,
    InvalidCustomerError,
    InvalidMedicationHistoryEntryError,
)
from pharmacy_os.modules.crm.domain.ports import CustomerRepository

__all__ = [
    "Allergy",
    "AllergySeverity",
    "Condition",
    "Customer",
    "MedicationHistoryEntry",
    "MedicationHistorySource",
    "CrmError",
    "DuplicateAllergyError",
    "DuplicateConditionError",
    "InvalidConditionError",
    "InvalidCustomerError",
    "InvalidMedicationHistoryEntryError",
    "CustomerRepository",
]
