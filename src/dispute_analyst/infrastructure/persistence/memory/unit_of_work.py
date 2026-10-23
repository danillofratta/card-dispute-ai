"""UnitOfWork kept in memory: nothing is saved until commit."""

import copy
from types import TracebackType
from typing import Self

from dispute_analyst.infrastructure.persistence.memory.dispute_repository import (
    InMemoryDisputeRepository,
)
from dispute_analyst.infrastructure.persistence.memory.store import InMemoryStore


class InMemoryUnitOfWork:
    """Saves the tracked disputes and moves their events to the outbox in one step."""

    def __init__(self, store: InMemoryStore) -> None:
        """Bind the unit of work to the process-wide store."""
        self._store = store
        self.disputes = InMemoryDisputeRepository(store)

    async def __aenter__(self) -> Self:
        """Start with a fresh repository: nothing tracked yet."""
        self.disputes = InMemoryDisputeRepository(self._store)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Always discard what was not committed, with or without an exception."""
        await self.rollback()

    async def commit(self) -> None:
        """Save each tracked dispute and its events together, like one database transaction."""
        tracked = self.disputes.tracked()
        events = [event for dispute in tracked for event in dispute.pull_events()]
        self._store.disputes.update({dispute.id: copy.deepcopy(dispute) for dispute in tracked})
        self._store.outbox.extend(events)
        self.disputes = InMemoryDisputeRepository(self._store)

    async def rollback(self) -> None:
        """Forget every staged change."""
        self.disputes = InMemoryDisputeRepository(self._store)
