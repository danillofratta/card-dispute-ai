"""HTTP contract of analyze_dispute: the response body."""

from typing import Self
from uuid import UUID

from pydantic import BaseModel

from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.domain.enums.proposal_outcome import ProposalOutcome
from dispute_analyst.domain.value_objects.decision_proposal import DecisionProposal
from dispute_analyst.features.disputes.analyze_dispute.result import AnalyzeDisputeResult


class ProposalResponse(BaseModel):
    """What the agent proposed. The amount is text with two decimals."""

    outcome: ProposalOutcome
    justification: str
    citations: list[str]
    amount: str | None
    currency: str | None

    @classmethod
    def from_proposal(cls, proposal: DecisionProposal) -> Self:
        """Map the domain proposal to the HTTP shape."""
        amount = proposal.amount
        return cls(
            outcome=proposal.outcome,
            justification=proposal.justification,
            citations=list(proposal.citations),
            amount=None if amount is None else f"{amount.amount:.2f}",
            currency=None if amount is None else amount.currency,
        )


class AnalyzeDisputeResponse(BaseModel):
    """Body of POST /disputes/{dispute_id}/analysis: the decision and what it was based on."""

    id: UUID
    status: DisputeStatus
    proposal: ProposalResponse | None
    failure: str | None

    @classmethod
    def from_result(cls, result: AnalyzeDisputeResult) -> Self:
        """Map the use case result to the HTTP shape."""
        proposal = result.proposal
        return cls(
            id=result.dispute_id,
            status=result.status,
            proposal=None if proposal is None else ProposalResponse.from_proposal(proposal),
            failure=result.failure,
        )
