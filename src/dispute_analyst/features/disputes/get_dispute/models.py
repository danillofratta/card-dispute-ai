"""HTTP contract of get_dispute: the response body."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel

from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.features.disputes.get_dispute.result import GetDisputeResult


class GetDisputeResponse(BaseModel):
    """Body of GET /disputes/{dispute_id}. Amounts are text with two decimals."""

    id: UUID
    customer_id: UUID
    transaction_id: UUID
    status: DisputeStatus
    reason: DisputeReason
    description: str
    currency: str
    disputed_amount: str
    approved_amount: str | None
    opened_at: datetime
    merchant: str | None
    card_last_four: str | None

    @classmethod
    def from_result(cls, result: GetDisputeResult) -> Self:
        """Map the use case result to the HTTP shape."""
        approved = result.approved_amount
        return cls(
            id=result.id,
            customer_id=result.customer_id,
            transaction_id=result.transaction_id,
            status=result.status,
            reason=result.reason,
            description=result.description,
            currency=result.disputed_amount.currency,
            disputed_amount=f"{result.disputed_amount.amount:.2f}",
            approved_amount=None if approved is None else f"{approved.amount:.2f}",
            opened_at=result.opened_at,
            merchant=result.merchant,
            card_last_four=result.card_last_four,
        )
