"""CRM domain: customer/patient master data. Framework-free."""

from pharmacy_os.modules.crm.domain.entities import (
    ANONYMISED_NAME,
    Allergy,
    AllergySeverity,
    Condition,
    ConsentPurpose,
    Customer,
    CustomerConsent,
    MedicationHistoryEntry,
    MedicationHistorySource,
)
from pharmacy_os.modules.crm.domain.exceptions import (
    ConsentRequiredError,
    CrmError,
    CustomerAnonymisedError,
    DuplicateAllergyError,
    DuplicateConditionError,
    InvalidConditionError,
    InvalidConsentError,
    InvalidCustomerError,
    InvalidMedicationHistoryEntryError,
)
from pharmacy_os.modules.crm.domain.ports import CustomerRepository

__all__ = [
    "ANONYMISED_NAME",
    "Allergy",
    "AllergySeverity",
    "Condition",
    "ConsentPurpose",
    "ConsentRequiredError",
    "CrmError",
    "Customer",
    "CustomerAnonymisedError",
    "CustomerConsent",
    "CustomerRepository",
    "DuplicateAllergyError",
    "DuplicateConditionError",
    "InvalidConditionError",
    "InvalidConsentError",
    "InvalidCustomerError",
    "InvalidMedicationHistoryEntryError",
    "MedicationHistoryEntry",
    "MedicationHistorySource",
]
