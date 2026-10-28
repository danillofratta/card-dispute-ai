import json
from typing import Any
from uuid import UUID, uuid4

from langchain_core.tools import BaseTool

from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.value_objects.money import Money
from dispute_analyst.features.disputes.analyze_dispute.gateway import DisputeCaseDto
from dispute_analyst.infrastructure.agents.baseline.tools import build_tools
from dispute_analyst.infrastructure.core_banking.seed import (
    TX_ANA_ONLINE_STORE,
    TX_ANA_STREAMING,
    TX_ANA_STREAMING_AGAIN,
)
from dispute_analyst.infrastructure.core_banking.simulated_core_banking import (
    SimulatedCoreBanking,
)
from dispute_analyst.infrastructure.merchants.seed import ORDER_ANA_ONLINE_STORE
from dispute_analyst.infrastructure.merchants.simulated_merchants import SimulatedMerchants


def tools_for(transaction_id: UUID) -> dict[str, BaseTool]:
    case = DisputeCaseDto(
        dispute_id=uuid4(),
        transaction_id=transaction_id,
        reason=DisputeReason.DUPLICATE_CHARGE,
        description="Fui cobrado duas vezes.",
        disputed_amount=Money.of("129.90"),
    )
    tools = build_tools(case, SimulatedCoreBanking(), SimulatedMerchants())
    return {tool.name: tool for tool in tools}


async def run(tools: dict[str, BaseTool], name: str) -> Any:
    return json.loads(await tools[name].ainvoke({}))


def test_the_tools_take_no_arguments() -> None:
    tools = tools_for(TX_ANA_STREAMING_AGAIN)

    assert set(tools) == {"get_disputed_transaction", "get_card_history", "get_merchant_order"}
    assert all(tool.args == {} for tool in tools.values())


async def test_the_disputed_transaction_carries_the_id_to_cite() -> None:
    transaction = await run(tools_for(TX_ANA_STREAMING_AGAIN), "get_disputed_transaction")

    assert transaction["id"] == f"transaction:{TX_ANA_STREAMING_AGAIN}"
    assert transaction["merchant"] == "Streaming Plus"
    assert transaction["amount"] == "129.90"


async def test_the_card_history_shows_the_twin_charge() -> None:
    history = await run(tools_for(TX_ANA_STREAMING_AGAIN), "get_card_history")

    assert [t["id"] for t in history["transactions"]] == [
        f"transaction:{TX_ANA_ONLINE_STORE}",
        f"transaction:{TX_ANA_STREAMING}",
        f"transaction:{TX_ANA_STREAMING_AGAIN}",
    ]


async def test_an_online_order_shows_its_delivery_proof() -> None:
    found = await run(tools_for(TX_ANA_ONLINE_STORE), "get_merchant_order")

    assert found["order"]["id"] == f"order:{ORDER_ANA_ONLINE_STORE}"
    assert found["order"]["delivery_status"] == "delivered"
    assert found["order"]["tracking_code"] == "BR123456789"


async def test_a_charge_that_is_not_an_order_says_so() -> None:
    found = await run(tools_for(TX_ANA_STREAMING), "get_merchant_order")

    assert found["order"] is None


async def test_an_unknown_transaction_is_an_answer_not_a_crash() -> None:
    tools = tools_for(uuid4())

    assert "error" in await run(tools, "get_disputed_transaction")
    assert "error" in await run(tools, "get_card_history")
