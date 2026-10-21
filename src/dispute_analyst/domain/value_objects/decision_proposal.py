"""DecisionProposal: what the analysis agent suggests. The Dispute aggregate decides."""

from __future__ import annotations

from dataclasses import dataclass

from dispute_analyst.domain.enums.proposal_outcome import ProposalOutcome
from dispute_analyst.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class DecisionProposal:
    """No validation here on purpose: a bad proposal is judged by the aggregate, not rejected."""

    outcome: ProposalOutcome
    justification: str
    citations: tuple[str, ...] = ()
    amount: Money | None = None
