"""CRM domain: customer/patient master data. Framework-free."""

from pharmacy_os.modules.crm.domain.entities import (
    ANONYMISED_NAME,
    DEFAULT_TERMS_VERSION,
    Allergy,
    AllergySeverity,
    Condition,
    ConsentBasis,
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
    "DEFAULT_TERMS_VERSION",
    "ANONYMISED_NAME",
    "Allergy",
    "AllergySeverity",
    "Condition",
    "ConsentBasis",
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
