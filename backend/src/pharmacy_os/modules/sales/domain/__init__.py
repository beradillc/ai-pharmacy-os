"""Sales domain: POS orders, payments, returns and the Rx rule. Framework-free."""

from pharmacy_os.modules.sales.domain.entities import (
    Payment,
    PaymentMethod,
    SaleLine,
    SalesOrder,
    SaleStatus,
)
from pharmacy_os.modules.sales.domain.events import SaleCompleted, SaleReturned, SoldItem
from pharmacy_os.modules.sales.domain.exceptions import (
    EmptyOrderError,
    InvalidOrderStateError,
    InvalidPrescriptionRefError,
    InvalidReturnError,
    PrescriptionRequiredError,
    SalesError,
    UnderpaidError,
)
from pharmacy_os.modules.sales.domain.ports import (
    DrugInfo,
    DrugInfoProvider,
    PrescriptionInfo,
    PrescriptionInfoProvider,
    SalesRepository,
)
from pharmacy_os.modules.sales.domain.rules import (
    ensure_prescription_valid_for_sale,
    ensure_rx_for_etc,
)

__all__ = [
    "Payment",
    "PaymentMethod",
    "SaleLine",
    "SalesOrder",
    "SaleStatus",
    "SaleCompleted",
    "SaleReturned",
    "SoldItem",
    "EmptyOrderError",
    "InvalidOrderStateError",
    "InvalidPrescriptionRefError",
    "InvalidReturnError",
    "PrescriptionRequiredError",
    "SalesError",
    "UnderpaidError",
    "SalesRepository",
    "DrugInfo",
    "DrugInfoProvider",
    "PrescriptionInfo",
    "PrescriptionInfoProvider",
    "ensure_prescription_valid_for_sale",
    "ensure_rx_for_etc",
]
