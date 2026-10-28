"""AnalyzeDisputeResult: what the use case returns, in domain types."""

from dataclasses import dataclass
from uuid import UUID

from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.domain.value_objects.decision_proposal import DecisionProposal


@dataclass(frozen=True, slots=True)
class AnalyzeDisputeResult:
    """The status the domain decided, and the proposal it decided on.

    Without a proposal, failure says why the analyzer could not make one.
    """

    dispute_id: UUID
    status: DisputeStatus
    proposal: DecisionProposal | None = None
    failure: str | None = None
