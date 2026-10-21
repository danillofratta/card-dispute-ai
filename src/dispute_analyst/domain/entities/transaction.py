"""Transaction: a charge on a card, the thing a customer disputes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from dispute_analyst.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class Transaction:
    """Read-only snapshot of a card charge."""

    id: UUID
    card_id: UUID
    amount: Money
    merchant: str
    occurred_at: datetime

    def __post_init__(self) -> None:
        if self.amount == Money.zero(self.amount.currency):
            raise ValueError("transaction amount must be greater than zero")
        if not self.merchant.strip():
            raise ValueError("merchant must not be blank")
        # A naive datetime has no offset: "10:00" in which time zone?
        if self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
