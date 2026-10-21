from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Base class. kw_only lets subclasses add required fields after occurred_at's default."""

    dispute_id: UUID
    occurred_at: datetime = field(default_factory=_now)
