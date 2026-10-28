"""Merchants backed by fixed synthetic orders, standing in for the merchants' real APIs."""

from collections.abc import Iterable
from uuid import UUID

from dispute_analyst.domain.entities.merchant_order import MerchantOrder
from dispute_analyst.infrastructure.merchants.seed import ORDERS


class SimulatedMerchants:
    """Answers from a fixed list of orders."""

    def __init__(self, orders: Iterable[MerchantOrder] = ORDERS) -> None:
        """Index the orders by the transaction that paid for them. Tests can pass their own."""
        self._orders = {order.transaction_id: order for order in orders}

    async def get_order_by_transaction(self, transaction_id: UUID) -> MerchantOrder | None:
        """Return the order this transaction paid for, or None if there is none."""
        return self._orders.get(transaction_id)
