"""GetDisputeQuery: which dispute to show."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetDisputeQuery:
    """CQRS query: read one dispute by id."""

    dispute_id: UUID
