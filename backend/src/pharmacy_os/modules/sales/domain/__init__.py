"""Sales domain: POS orders, payments, returns and the Rx rule. Framework-free."""

from pharmacy_os.modules.sales.domain.entities import (
    Payment,
    PaymentMethod,
    SaleLine,
    SalesOrder,
    SaleStatus,
)
from pharmacy_os.modules.sales.domain.events import SaleCompleted, SoldItem
from pharmacy_os.modules.sales.domain.exceptions import (
    EmptyOrderError,
    InvalidOrderStateError,
    InvalidReturnError,
    PrescriptionRequiredError,
    SalesError,
    UnderpaidError,
)
from pharmacy_os.modules.sales.domain.ports import SalesRepository
from pharmacy_os.modules.sales.domain.rules import ensure_rx_for_etc

__all__ = [
    "Payment",
    "PaymentMethod",
    "SaleLine",
    "SalesOrder",
    "SaleStatus",
    "SaleCompleted",
    "SoldItem",
    "EmptyOrderError",
    "InvalidOrderStateError",
    "InvalidReturnError",
    "PrescriptionRequiredError",
    "SalesError",
    "UnderpaidError",
    "SalesRepository",
    "ensure_rx_for_etc",
]
