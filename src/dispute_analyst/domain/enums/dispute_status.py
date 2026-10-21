"""Every status a dispute can be in, and which moves between them are allowed."""

from __future__ import annotations

from enum import StrEnum


class DisputeStatus(StrEnum):
    OPEN = "open"
    UNDER_ANALYSIS = "under_analysis"
    AWAITING_APPROVAL = "awaiting_approval"
    MANUAL_REVIEW = "manual_review"
    APPROVED = "approved"
    DENIED = "denied"
    REFUNDED = "refunded"
    REFUND_FAILED = "refund_failed"

    def can_move_to(self, target: DisputeStatus) -> bool:
        return target in _ALLOWED_MOVES[self]


# The state machine from AGENTS.md. A status missing from the left side is final.
_ALLOWED_MOVES: dict[DisputeStatus, frozenset[DisputeStatus]] = {
    DisputeStatus.OPEN: frozenset({DisputeStatus.UNDER_ANALYSIS}),
    DisputeStatus.UNDER_ANALYSIS: frozenset(
        {
            DisputeStatus.APPROVED,
            DisputeStatus.DENIED,
            DisputeStatus.AWAITING_APPROVAL,
            DisputeStatus.MANUAL_REVIEW,
        }
    ),
    DisputeStatus.AWAITING_APPROVAL: frozenset({DisputeStatus.APPROVED, DisputeStatus.DENIED}),
    DisputeStatus.MANUAL_REVIEW: frozenset({DisputeStatus.APPROVED, DisputeStatus.DENIED}),
    DisputeStatus.APPROVED: frozenset({DisputeStatus.REFUNDED, DisputeStatus.REFUND_FAILED}),
    DisputeStatus.REFUND_FAILED: frozenset({DisputeStatus.REFUNDED, DisputeStatus.MANUAL_REVIEW}),
    DisputeStatus.DENIED: frozenset(),
    DisputeStatus.REFUNDED: frozenset(),
}
