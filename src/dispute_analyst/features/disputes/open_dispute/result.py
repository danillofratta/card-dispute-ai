"""OpenDisputeResult: what the use case returns, in domain types."""

from dataclasses import dataclass
from uuid import UUID

from dispute_analyst.domain.enums.dispute_status import DisputeStatus


@dataclass(frozen=True, slots=True)
class OpenDisputeResult:
    """Result of opening a dispute."""

    dispute_id: UUID
    status: DisputeStatus
