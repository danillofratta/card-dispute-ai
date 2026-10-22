from dataclasses import dataclass, field
from uuid import UUID

from dispute_analyst.domain.aggregates.dispute import Dispute
from dispute_analyst.domain.events.domain_event import DomainEvent


@dataclass
class InMemoryStore:
    """In-memory store for persisting data during runtime."""

    disputes: dict[UUID, Dispute] = field(default_factory=dict)
    outbox: list[DomainEvent] = field(default_factory=list)
