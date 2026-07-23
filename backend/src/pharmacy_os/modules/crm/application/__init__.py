"""Crm application layer: use-cases and DTOs."""

from pharmacy_os.modules.crm.application.dto import (
    AddAllergyInput,
    AddConditionInput,
    AllergyOutput,
    ConditionOutput,
    ConsentOutput,
    CreateCustomerInput,
    CustomerOutput,
    MedicationHistoryItemInput,
    MedicationHistoryOutput,
    RecordConsentInput,
)
from pharmacy_os.modules.crm.application.service import CrmService

__all__ = [
    "AddAllergyInput",
    "AddConditionInput",
    "AllergyOutput",
    "ConditionOutput",
    "ConsentOutput",
    "CreateCustomerInput",
    "CrmService",
    "CustomerOutput",
    "MedicationHistoryItemInput",
    "MedicationHistoryOutput",
    "RecordConsentInput",
]
