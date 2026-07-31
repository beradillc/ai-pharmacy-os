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
    AllergyAcknowledgementRequiredError,
    EmptyOrderError,
    InvalidOrderStateError,
    InvalidPrescriptionRefError,
    InvalidReturnError,
    PrescriptionRequiredError,
    PriceOverrideReasonRequiredError,
    SalesError,
    UnderpaidError,
)
from pharmacy_os.modules.sales.domain.ports import (
    AllergyRisk,
    AllergyRiskProvider,
    DrugInfo,
    DrugInfoProvider,
    DrugSalesAggRow,
    OrderRevenueRow,
    PrescriptionInfo,
    PrescriptionInfoProvider,
    SalesOrderListRow,
    SalesRepository,
)
from pharmacy_os.modules.sales.domain.rules import (
    ensure_allergy_acknowledged,
    ensure_prescription_valid_for_sale,
    ensure_price_override_acknowledged,
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
    "AllergyAcknowledgementRequiredError",
    "PriceOverrideReasonRequiredError",
    "EmptyOrderError",
    "InvalidOrderStateError",
    "InvalidPrescriptionRefError",
    "InvalidReturnError",
    "PrescriptionRequiredError",
    "SalesError",
    "UnderpaidError",
    "SalesRepository",
    "OrderRevenueRow",
    "SalesOrderListRow",
    "DrugSalesAggRow",
    "AllergyRisk",
    "AllergyRiskProvider",
    "DrugInfo",
    "DrugInfoProvider",
    "PrescriptionInfo",
    "PrescriptionInfoProvider",
    "ensure_allergy_acknowledged",
    "ensure_price_override_acknowledged",
    "ensure_prescription_valid_for_sale",
    "ensure_rx_for_etc",
]
