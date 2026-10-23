from dataclasses import dataclass
from uuid import UUID

from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class OpenDisputeCommand:
    """CQRS command: open a dispute for one card transaction."""

    customer_id: UUID
    transaction_id: UUID
    reason: DisputeReason
    description: str
    disputed_amount: Money | None = None
