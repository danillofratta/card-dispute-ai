"""Money value object: a non-negative amount in a currency, backed by Decimal."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from functools import total_ordering
from typing import Self

DEFAULT_CURRENCY = "BRL"

_CENTS = Decimal("0.01")
_CURRENCY_CODE = re.compile(r"[A-Z]{3}")


@total_ordering
@dataclass(frozen=True, slots=True)
class Money:
    """A non-negative amount with at most two decimal places, in one currency."""

    amount: Decimal
    currency: str = DEFAULT_CURRENCY

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError(f"amount must be a Decimal, got {type(self.amount).__name__}")
        # Checked before any comparison: Decimal("NaN") < 0 raises InvalidOperation.
        if not self.amount.is_finite():
            raise ValueError(f"amount must be finite, got {self.amount}")
        if self.amount < 0:
            raise ValueError(f"amount must not be negative, got {self.amount}")
        if self.amount != self.amount.quantize(_CENTS):
            raise ValueError(f"amount must have at most 2 decimal places, got {self.amount}")
        if not _CURRENCY_CODE.fullmatch(self.currency):
            raise ValueError(f"currency must be 3 uppercase letters, got {self.currency!r}")

    @classmethod
    def of(cls, amount: str, currency: str = DEFAULT_CURRENCY) -> Self:
        """Build from a string such as "150.00", so callers never touch floats."""
        if not isinstance(amount, str):
            raise TypeError(f"amount must be a str, got {type(amount).__name__}")
        try:
            value = Decimal(amount)
        except InvalidOperation as error:
            raise ValueError(f"amount is not a number: {amount!r}") from error
        return cls(value, currency)

    @classmethod
    def zero(cls, currency: str = DEFAULT_CURRENCY) -> Self:
        return cls(Decimal("0"), currency)

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._ensure_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._ensure_same_currency(other)
        # A negative result is rejected by __post_init__.
        return Money(self.amount - other.amount, self.currency)

    def __lt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._ensure_same_currency(other)
        return self.amount < other.amount

    def __str__(self) -> str:
        return f"{self.currency} {self.amount.quantize(_CENTS)}"

    def _ensure_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(f"currency mismatch: {self.currency} and {other.currency}")