"""Immutable value objects shared across domains.

These carry no framework dependency and are safe to import anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_CENTS = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class Money:
    """A monetary amount in a single currency (default VND).

    Amounts are stored as :class:`~decimal.Decimal` — never float — and
    quantised to 2 decimal places to avoid representation drift.
    """

    amount: Decimal
    currency: str = "VND"

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", Decimal(self.amount).quantize(_CENTS, ROUND_HALF_UP))

    def _check(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(f"Currency mismatch: {self.currency} vs {other.currency}")

    def add(self, other: Money) -> Money:
        self._check(other)
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: Money) -> Money:
        self._check(other)
        return Money(self.amount - other.amount, self.currency)

    def multiply(self, factor: Decimal | int) -> Money:
        return Money(self.amount * Decimal(factor), self.currency)

    def is_negative(self) -> bool:
        return self.amount < 0

    @classmethod
    def zero(cls, currency: str = "VND") -> Money:
        return cls(Decimal("0"), currency)


@dataclass(frozen=True, slots=True)
class Quantity:
    """A quantity of goods expressed in a named unit (e.g. 'viên', 'vỉ')."""

    value: Decimal
    unit: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", Decimal(self.value))
        if self.value < 0:
            raise ValueError("Quantity cannot be negative")
        if not self.unit:
            raise ValueError("Quantity requires a unit")

    def add(self, other: Quantity) -> Quantity:
        if self.unit != other.unit:
            raise ValueError(f"Unit mismatch: {self.unit} vs {other.unit}")
        return Quantity(self.value + other.value, self.unit)
