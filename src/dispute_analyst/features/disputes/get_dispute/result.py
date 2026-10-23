"""GetDisputeResult: everything an analyst sees about one dispute, in domain types."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class GetDisputeResult:
    """The dispute plus what the screen needs from the transaction and the card.

    The Dispute aggregate references the transaction only by id; this read shape joins them.
    """

    id: UUID
    customer_id: UUID
    transaction_id: UUID
    status: DisputeStatus
    reason: DisputeReason
    description: str
    disputed_amount: Money
    approved_amount: Money | None
    opened_at: datetime
    merchant: str | None
    card_last_four: str | None
