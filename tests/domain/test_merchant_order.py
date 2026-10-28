from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from dispute_analyst.domain.entities.merchant_order import MerchantOrder
from dispute_analyst.domain.enums.delivery_status import DeliveryStatus

DELIVERED_AT = datetime(2026, 10, 4, 15, tzinfo=UTC)


def make_order(
    *,
    merchant: str = "Online Store",
    delivery_status: DeliveryStatus = DeliveryStatus.DELIVERED,
    tracking_code: str | None = "BR123456789",
    delivered_at: datetime | None = DELIVERED_AT,
) -> MerchantOrder:
    return MerchantOrder(
        id=uuid4(),
        transaction_id=uuid4(),
        merchant=merchant,
        delivery_status=delivery_status,
        tracking_code=tracking_code,
        delivered_at=delivered_at,
    )


def test_a_delivered_order_carries_its_proof() -> None:
    order = make_order()

    assert order.delivery_status is DeliveryStatus.DELIVERED
    assert order.tracking_code == "BR123456789"
    assert order.delivered_at == DELIVERED_AT


def test_an_order_not_delivered_has_no_delivery_date() -> None:
    order = make_order(
        delivery_status=DeliveryStatus.NOT_DELIVERED, tracking_code=None, delivered_at=None
    )

    assert order.delivered_at is None


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"merchant": "  "}, id="blank merchant"),
        pytest.param({"tracking_code": " "}, id="blank tracking code"),
        pytest.param({"delivered_at": None}, id="delivered without a date"),
        pytest.param(
            {"delivery_status": DeliveryStatus.NOT_DELIVERED}, id="not delivered with a date"
        ),
        pytest.param({"delivered_at": datetime(2026, 10, 4, 15)}, id="naive delivery date"),
    ],
)
def test_rejects_an_invalid_order(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        make_order(**changes)
