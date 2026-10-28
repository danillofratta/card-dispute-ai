from datetime import UTC, datetime

import pytest

from dispute_analyst.domain.enums.delivery_status import DeliveryStatus
from dispute_analyst.infrastructure.core_banking.seed import (
    TX_ANA_ONLINE_STORE,
    TX_ANA_STREAMING,
    TX_BRUNO_ELECTRONICS,
)
from dispute_analyst.infrastructure.merchants.seed import ORDER_ANA_ONLINE_STORE
from dispute_analyst.infrastructure.merchants.sqlalchemy_merchants import SqlAlchemyMerchants
from dispute_analyst.infrastructure.persistence.sqlalchemy.database import Database

pytestmark = pytest.mark.integration


async def test_translates_a_delivered_order(database: Database) -> None:
    merchants = SqlAlchemyMerchants(database.session_factory)

    order = await merchants.get_order_by_transaction(TX_ANA_ONLINE_STORE)

    assert order is not None
    assert order.id == ORDER_ANA_ONLINE_STORE
    assert order.delivery_status is DeliveryStatus.DELIVERED
    assert order.tracking_code == "BR123456789"
    assert order.delivered_at == datetime(2026, 10, 4, 15, tzinfo=UTC)


async def test_translates_an_order_not_delivered(database: Database) -> None:
    merchants = SqlAlchemyMerchants(database.session_factory)

    order = await merchants.get_order_by_transaction(TX_BRUNO_ELECTRONICS)

    assert order is not None
    assert order.delivery_status is DeliveryStatus.NOT_DELIVERED
    assert order.tracking_code is None
    assert order.delivered_at is None


async def test_a_charge_with_no_order_is_none(database: Database) -> None:
    merchants = SqlAlchemyMerchants(database.session_factory)

    assert await merchants.get_order_by_transaction(TX_ANA_STREAMING) is None
