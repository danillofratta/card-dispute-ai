"""Read-only tools the baseline agent investigates with.

Each tool is bound to one case and takes no arguments: the model can read the disputed charge,
its card's history and its order, and nothing else. A prompt injection in the customer's text
cannot make it look up another customer's data, and there is no id for a small model to mistype.
"""

import json
from datetime import timedelta
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from dispute_analyst.application.ports.core_banking import CoreBanking
from dispute_analyst.domain.entities.merchant_order import MerchantOrder
from dispute_analyst.domain.entities.transaction import Transaction
from dispute_analyst.features.disputes.analyze_dispute.gateway import DisputeCaseDto
from dispute_analyst.infrastructure.merchants.merchants import Merchants

# Long enough to see a monthly subscription three times, short enough to keep the prompt small.
HISTORY_BEFORE = timedelta(days=120)
HISTORY_AFTER = timedelta(days=30)


def build_tools(
    case: DisputeCaseDto, core_banking: CoreBanking, merchants: Merchants
) -> list[BaseTool]:
    """The tools for one case. Each returns compact JSON, which costs fewer tokens than prose."""

    async def get_disputed_transaction() -> str:
        transaction = await core_banking.get_transaction(case.transaction_id)
        if transaction is None:
            return _json({"error": "the bank does not know this transaction"})
        return _json(_transaction(transaction))

    async def get_card_history() -> str:
        disputed = await core_banking.get_transaction(case.transaction_id)
        if disputed is None:
            return _json({"error": "the bank does not know this transaction"})
        history = await core_banking.list_card_transactions(
            disputed.card_id,
            since=disputed.occurred_at - HISTORY_BEFORE,
            until=disputed.occurred_at + HISTORY_AFTER,
        )
        return _json({"transactions": [_transaction(t) for t in history]})

    async def get_merchant_order() -> str:
        order = await merchants.get_order_by_transaction(case.transaction_id)
        if order is None:
            return _json({"order": None, "note": "this charge was not an online order"})
        return _json({"order": _order(order)})

    return [
        StructuredTool.from_function(
            coroutine=get_disputed_transaction,
            name="get_disputed_transaction",
            description="The disputed charge: merchant, amount and when it happened.",
        ),
        StructuredTool.from_function(
            coroutine=get_card_history,
            name="get_card_history",
            description=(
                "Every charge on the same card from 120 days before to 30 days after the "
                "disputed one, oldest first, including the disputed charge itself."
            ),
        ),
        StructuredTool.from_function(
            coroutine=get_merchant_order,
            name="get_merchant_order",
            description=(
                "The merchant's order paid by the disputed charge, with its delivery status, "
                "tracking code and delivery date. Only online purchases have one."
            ),
        ),
    ]


def _transaction(transaction: Transaction) -> dict[str, Any]:
    return {
        "id": f"transaction:{transaction.id}",
        "merchant": transaction.merchant,
        "amount": f"{transaction.amount.amount:.2f}",
        "currency": transaction.amount.currency,
        "occurred_at": transaction.occurred_at.isoformat(),
    }


def _order(order: MerchantOrder) -> dict[str, Any]:
    return {
        "id": f"order:{order.id}",
        "merchant": order.merchant,
        "delivery_status": order.delivery_status.value,
        "tracking_code": order.tracking_code,
        "delivered_at": None if order.delivered_at is None else order.delivered_at.isoformat(),
    }


def _json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
