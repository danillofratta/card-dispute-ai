"""MerchantOrder: an online order paid by a card transaction, as the merchant knows it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from dispute_analyst.domain.enums.delivery_status import DeliveryStatus


@dataclass(frozen=True, slots=True)
class MerchantOrder:
    """Read-only snapshot of an order. The proof for a "never delivered" dispute."""

    id: UUID
    transaction_id: UUID
    merchant: str
    delivery_status: DeliveryStatus
    tracking_code: str | None = None
    delivered_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.merchant.strip():
            raise ValueError("merchant must not be blank")
        if self.tracking_code is not None and not self.tracking_code.strip():
            raise ValueError("tracking_code must be None or non-blank")
        delivered = self.delivery_status is DeliveryStatus.DELIVERED
        if delivered != (self.delivered_at is not None):
            raise ValueError("delivered_at is required for a delivered order, and only for one")
        if self.delivered_at is not None and self.delivered_at.utcoffset() is None:
            raise ValueError("delivered_at must be timezone-aware")
