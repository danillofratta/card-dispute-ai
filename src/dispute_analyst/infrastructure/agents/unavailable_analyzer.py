"""Gateway used when no model is configured: every dispute goes to manual review."""

from dispute_analyst.domain.value_objects.decision_proposal import DecisionProposal
from dispute_analyst.features.disputes.analyze_dispute.exceptions import (
    AnalyzeDisputeUnavailableError,
)
from dispute_analyst.features.disputes.analyze_dispute.gateway import (
    DisputeCaseDto,
)


class UnavailableAnalyzer:
    """Always unavailable, with the reason it was given. The API keeps working without a model."""

    def __init__(self, reason: str) -> None:
        self._reason = reason

    async def analyze(self, case: DisputeCaseDto) -> DecisionProposal:
        """Never proposes: raise, so the handler sends the dispute to manual review."""
        raise AnalyzeDisputeUnavailableError(self._reason)
