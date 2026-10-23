"""HTTP contract of list_queue: the response body."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel

from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.features.disputes.list_queue.result import ListQueueResult, QueueItem


class QueueItemResponse(BaseModel):
    """One line of the queue. Amounts are text with two decimals."""

    id: UUID
    status: DisputeStatus
    reason: DisputeReason
    currency: str
    disputed_amount: str
    opened_at: datetime

    @classmethod
    def from_item(cls, item: QueueItem) -> Self:
        """Map one queue item to the HTTP shape."""
        return cls(
            id=item.id,
            status=item.status,
            reason=item.reason,
            currency=item.disputed_amount.currency,
            disputed_amount=f"{item.disputed_amount.amount:.2f}",
            opened_at=item.opened_at,
        )


class ListQueueResponse(BaseModel):
    """Body of GET /disputes."""

    items: list[QueueItemResponse]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_result(cls, result: ListQueueResult, *, limit: int, offset: int) -> Self:
        """Map the use case result to the HTTP shape, echoing the page asked for."""
        return cls(
            items=[QueueItemResponse.from_item(item) for item in result.items],
            total=result.total,
            limit=limit,
            offset=offset,
        )
