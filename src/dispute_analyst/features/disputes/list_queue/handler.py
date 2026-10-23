"""ListQueueHandler: reads one page of the dispute queue through the repository."""

from dispute_analyst.domain.repositories.dispute_repository import DisputeRepository
from dispute_analyst.features.disputes.list_queue.query import ListQueueQuery
from dispute_analyst.features.disputes.list_queue.result import ListQueueResult, QueueItem


class ListQueueHandler:
    """CQRS query handler. Reads aggregates through the repository and never changes them."""

    def __init__(self, disputes: DisputeRepository) -> None:
        """Receive the repository port; the endpoint provides the implementation."""
        self._disputes = disputes

    async def handle(self, query: ListQueueQuery) -> ListQueueResult:
        """Return one page of the queue, oldest first, and the total that matches."""
        disputes = await self._disputes.list_by_status(
            query.status, limit=query.limit, offset=query.offset
        )
        total = await self._disputes.count_by_status(query.status)

        items = tuple(
            QueueItem(
                id=dispute.id,
                status=dispute.status,
                reason=dispute.reason,
                disputed_amount=dispute.disputed_amount,
                opened_at=dispute.opened_at,
            )
            for dispute in disputes
        )
        return ListQueueResult(items=items, total=total)
