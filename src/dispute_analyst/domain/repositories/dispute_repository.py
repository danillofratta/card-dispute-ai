"""DisputeRepository: the collection of Dispute aggregates, as a DDD repository interface."""

from typing import Protocol
from uuid import UUID

from dispute_analyst.domain.aggregates.dispute import Dispute


class DisputeRepository(Protocol):
    """The collection of Dispute aggregates, as a DDD repository interface."""

    async def get_by_id(self, dispute_id: UUID) -> Dispute | None:
        """Retrieve a Dispute aggregate by its ID, or return None if not found."""

    async def add(self, dispute: Dispute) -> None:
        """Add a new Dispute aggregate to the repository."""
