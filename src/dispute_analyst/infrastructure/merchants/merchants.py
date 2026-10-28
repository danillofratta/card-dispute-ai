"""Merchants: what the merchant knows about an order, another bounded context.

The interface lives here, not in application/ports: only infrastructure uses it (the analysis
agent's tools). If a slice ever needs it, it moves to application/ports, like CoreBanking.
"""

from typing import Protocol
from uuid import UUID

from dispute_analyst.domain.entities.merchant_order import MerchantOrder


class Merchants(Protocol):
    """Read the merchants' orders, to check whether a product was delivered."""

    async def get_order_by_transaction(self, transaction_id: UUID) -> MerchantOrder | None:
        """Return the order this transaction paid for, or None if it was not an online order."""
