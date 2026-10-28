from uuid import uuid4

from dispute_analyst.domain.enums.delivery_status import DeliveryStatus
from dispute_analyst.infrastructure.core_banking.seed import (
    TX_ANA_ONLINE_STORE,
    TX_ANA_STREAMING,
    TX_BRUNO_ELECTRONICS,
)
from dispute_analyst.infrastructure.merchants.simulated_merchants import SimulatedMerchants


async def test_finds_the_order_a_transaction_paid_for() -> None:
    merchants = SimulatedMerchants()

    delivered = await merchants.get_order_by_transaction(TX_ANA_ONLINE_STORE)
    missing = await merchants.get_order_by_transaction(TX_BRUNO_ELECTRONICS)

    assert delivered is not None
    assert delivered.delivery_status is DeliveryStatus.DELIVERED
    assert delivered.tracking_code is not None
    assert missing is not None
    assert missing.delivery_status is DeliveryStatus.NOT_DELIVERED


async def test_a_charge_that_is_not_an_online_order_has_no_order() -> None:
    merchants = SimulatedMerchants()

    assert await merchants.get_order_by_transaction(TX_ANA_STREAMING) is None
    assert await merchants.get_order_by_transaction(uuid4()) is None


async def test_accepts_custom_orders() -> None:
    merchants = SimulatedMerchants(orders=[])

    assert await merchants.get_order_by_transaction(TX_ANA_ONLINE_STORE) is None
