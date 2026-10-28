"""Synthetic orders for the simulated merchants, over the fixed core bank transactions."""

from datetime import UTC, datetime
from uuid import UUID

from dispute_analyst.domain.entities.merchant_order import MerchantOrder
from dispute_analyst.domain.enums.delivery_status import DeliveryStatus
from dispute_analyst.infrastructure.core_banking.seed import (
    TX_ANA_ONLINE_STORE,
    TX_BRUNO_ELECTRONICS,
)

ORDER_ANA_ONLINE_STORE = UUID("00000000-0000-0000-0000-000000002001")
ORDER_BRUNO_ELECTRONICS = UUID("00000000-0000-0000-0000-000000002002")

ORDERS = (
    # Tracking code and delivery date: a "never delivered" dispute should be denied.
    MerchantOrder(
        id=ORDER_ANA_ONLINE_STORE,
        transaction_id=TX_ANA_ONLINE_STORE,
        merchant="Online Store",
        delivery_status=DeliveryStatus.DELIVERED,
        tracking_code="BR123456789",
        delivered_at=datetime(2026, 10, 4, 15, tzinfo=UTC),
    ),
    # No proof of delivery: a "never delivered" dispute should be approved, by a human
    # because 2450.00 is above the approval limit.
    MerchantOrder(
        id=ORDER_BRUNO_ELECTRONICS,
        transaction_id=TX_BRUNO_ELECTRONICS,
        merchant="Electronics Hub",
        delivery_status=DeliveryStatus.NOT_DELIVERED,
    ),
)
