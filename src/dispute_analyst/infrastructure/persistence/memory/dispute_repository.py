"""DisputeRepository kept in memory. Works on copies, like rows loaded from a database."""

import copy
from uuid import UUID

from dispute_analyst.domain.aggregates.dispute import Dispute
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
        if stored is None:
            return None

        dispute = copy.deepcopy(stored)
        self._tracked[dispute_id] = dispute

        return dispute

    async def add(self, dispute: Dispute) -> None:
        """Add a new dispute to the repository."""

        if dispute.id in self._tracked or dispute.id in self._store.disputes:
            raise ValueError(f"Dispute with ID {dispute.id} already exists.")

        self._tracked[dispute.id] = dispute

    def tracked(self) -> list[Dispute]:
        """Return a list of all tracked disputes."""
        return list(self._tracked.values())
