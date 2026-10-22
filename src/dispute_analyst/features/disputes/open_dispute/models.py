"""HTTP contract of open_dispute: request and response bodies."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.enums.dispute_status import DisputeStatus


class OpenDisputeRequest(BaseModel):
    """Body of POST /disputes. Amounts travel as text, never as JSON numbers (floats)."""

    customer_id: UUID
    transaction_id: UUID
    reason: DisputeReason
    description: str = Field(min_length=1, max_length=2000)
    disputed_amount: str | None = Field(
        default=None,
        pattern=r"^[0-9]+(\.[0-9]{1,2})?$",
        description="Amount in BRL, such as 129.90. Leave it out to dispute the whole transaction.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "customer_id": "00000000-0000-0000-0000-000000000001",
                    "transaction_id": "00000000-0000-0000-0000-000000001003",
                    "reason": "duplicate_charge",
                    "description": "I was charged twice for the same subscription.",
                }
            ]
        }
    )


class OpenDisputeResponse(BaseModel):
    """Body of the 201 response."""

    id: UUID
    status: DisputeStatus
