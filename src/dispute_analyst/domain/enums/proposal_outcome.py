"""What the analysis agent proposes to do with a dispute."""

from enum import StrEnum


class ProposalOutcome(StrEnum):
    APPROVE = "approve"
    DENY = "deny"
