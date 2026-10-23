"""DisputeRepository: the collection of Dispute aggregates, as a DDD repository interface."""

from typing import Protocol
from uuid import UUID

from dispute_analyst.domain.aggregates.dispute import Dispute
from dispute_analyst.domain.enums.dispute_status import DisputeStatus


class DisputeRepository(Protocol):
    """The collection of Dispute aggregates, as a DDD repository interface."""

    async def get_by_id(self, dispute_id: UUID) -> Dispute | None:
        """Retrieve a Dispute aggregate by its ID, or return None if not found."""

    async def list_by_status(
        self, status: DisputeStatus | None, *, limit: int, offset: int
    ) -> list[Dispute]:
        """List Dispute aggregates by their status; an empty list when none match."""

    async def count_by_status(self, status: DisputeStatus | None) -> int:
        """Count Dispute aggregates by their status."""

    async def add(self, dispute: Dispute) -> None:
        """Add a new Dispute aggregate to the repository."""
