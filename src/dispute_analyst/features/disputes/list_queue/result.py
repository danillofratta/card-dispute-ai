"""ListQueueResult: one page of the dispute queue, in domain types."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class QueueItem:
    """One line of the queue: only what the list screen shows."""

    id: UUID
    status: DisputeStatus
    reason: DisputeReason
    disputed_amount: Money
    opened_at: datetime


@dataclass(frozen=True, slots=True)
class ListQueueResult:
    """A page of the queue and how many disputes match in total."""

    items: tuple[QueueItem, ...]
    total: int
