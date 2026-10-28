from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AnalyzeDisputeCommand:
    """CQRS command: let the agent analyze an open dispute, and the domain decide."""

    dispute_id: UUID
