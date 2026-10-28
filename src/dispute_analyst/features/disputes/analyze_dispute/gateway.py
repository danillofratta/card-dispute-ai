from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.value_objects.decision_proposal import DecisionProposal
from dispute_analyst.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class DisputeCaseDto:
    """What the analyzer may read about a dispute.

    A frozen copy, not the aggregate: the analyzer can only propose, never call approve().
    """

    dispute_id: UUID
    transaction_id: UUID
    reason: DisputeReason
    description: str
    disputed_amount: Money


class AnalyzeDisputeGateway(Protocol):
    """Investigates a dispute and proposes a decision. The Dispute aggregate decides."""

    async def analyze(self, case: DisputeCaseDto) -> DecisionProposal:
        """Return a proposal, or raise AnalyzeDisputeUnavailableError."""
