"""HTTP adapter of list_queue: GET /disputes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from dispute_analyst.bootstrap.dependencies import DisputeRepositoryDependency
from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.features.disputes.list_queue.handler import ListQueueHandler
from dispute_analyst.features.disputes.list_queue.models import ListQueueResponse
from dispute_analyst.features.disputes.list_queue.query import ListQueueQuery

router = APIRouter(prefix="/disputes", tags=["Disputes"])


def get_handler(disputes: DisputeRepositoryDependency) -> ListQueueHandler:
    """Build the handler from the repository the composition root provides."""
    return ListQueueHandler(disputes)


@router.get("")
async def list_queue(
    handler: Annotated[ListQueueHandler, Depends(get_handler)],
    status: DisputeStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListQueueResponse:
    """The dispute queue, oldest first, optionally only one status."""
    query = ListQueueQuery(status=status, limit=limit, offset=offset)
    result = await handler.handle(query)
    return ListQueueResponse.from_result(result, limit=limit, offset=offset)
