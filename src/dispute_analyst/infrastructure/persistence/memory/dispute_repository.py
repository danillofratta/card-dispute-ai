"""DisputeRepository kept in memory. Works on copies, like rows loaded from a database."""

import copy
from uuid import UUID

from dispute_analyst.domain.aggregates.dispute import Dispute
from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.infrastructure.persistence.memory.store import InMemoryStore


class InMemoryDisputeRepository:
    """In-memory repository for managing disputes."""

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store
        self._tracked: dict[UUID, Dispute] = {}

    async def get_by_id(self, dispute_id: UUID) -> Dispute | None:
        """Retrieve a dispute by its ID, or return None if not found."""
        if dispute_id in self._tracked:
            return self._tracked[dispute_id]
        stored = self._store.disputes.get(dispute_id)
        return None if stored is None else self._load(stored)

    async def add(self, dispute: Dispute) -> None:
        """Add a new dispute to the repository."""
        if dispute.id in self._tracked or dispute.id in self._store.disputes:
            raise ValueError(f"Dispute with ID {dispute.id} already exists.")

        self._tracked[dispute.id] = dispute

    async def list_by_status(
        self, status: DisputeStatus | None, *, limit: int, offset: int
    ) -> list[Dispute]:
        """Oldest first; the id breaks ties so the order never changes between calls."""
        disputes = sorted(self._store.disputes.values(), key=lambda d: (d.opened_at, d.id))
        if status is not None:
            disputes = [dispute for dispute in disputes if dispute.status is status]
        return [self._load(dispute) for dispute in disputes[offset : offset + limit]]

    async def count_by_status(self, status: DisputeStatus | None) -> int:
        """Count disputes in this status, or all of them when status is None."""
        if status is None:
            return len(self._store.disputes)
        return sum(1 for dispute in self._store.disputes.values() if dispute.status is status)

    def tracked(self) -> list[Dispute]:
        """Return a list of all tracked disputes."""
        return list(self._tracked.values())

    def _load(self, stored: Dispute) -> Dispute:
        """Return this repository's copy of a stored dispute, the same one on every load."""
        if stored.id not in self._tracked:
            self._tracked[stored.id] = copy.deepcopy(stored)
        return self._tracked[stored.id]
