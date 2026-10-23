"""ListQueueQuery: which page of the dispute queue to show."""

from dataclasses import dataclass

from dispute_analyst.domain.enums.dispute_status import DisputeStatus


@dataclass(frozen=True, slots=True)
class ListQueueQuery:
    """CQRS query: disputes oldest first, optionally only one status."""

    status: DisputeStatus | None = None
    limit: int = 50
    offset: int = 0
