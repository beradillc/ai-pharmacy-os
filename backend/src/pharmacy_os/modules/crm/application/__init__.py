"""Crm application layer: use-cases and DTOs."""

from pharmacy_os.modules.crm.application.dto import (
    AddAllergyInput,
    AddConditionInput,
    AllergyOutput,
    ConditionOutput,
    CreateCustomerInput,
    CustomerOutput,
    MedicationHistoryOutput,
)
from pharmacy_os.modules.crm.application.service import CrmService

__all__ = [
    "AddAllergyInput",
    "AddConditionInput",
    "AllergyOutput",
    "ConditionOutput",
    "CreateCustomerInput",
    "CustomerOutput",
    "MedicationHistoryOutput",
    "CrmService",
]
