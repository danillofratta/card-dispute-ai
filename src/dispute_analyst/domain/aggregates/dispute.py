"""Dispute aggregate: the only place that decides what happens to a dispute."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from dispute_analyst.domain.entities.transaction import Transaction
from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.domain.enums.proposal_outcome import ProposalOutcome
from dispute_analyst.domain.events.dispute_event import (
    AnalysisStarted,
    ApprovalRequested,
    DisputeApproved,
    DisputeDenied,
    DisputeOpened,
    DisputeRefunded,
    DomainEvent,
    RefundFailed,
    SentToManualReview,
)
from dispute_analyst.domain.exceptions import DomainError, InvalidTransitionError
from dispute_analyst.domain.value_objects.approval_limit import ApprovalLimit
from dispute_analyst.domain.value_objects.decision_proposal import DecisionProposal
from dispute_analyst.domain.value_objects.money import Money

AGENT = "agent"
_HUMAN_DECISION_STATUSES = frozenset({DisputeStatus.AWAITING_APPROVAL, DisputeStatus.MANUAL_REVIEW})


class Dispute:
    """A customer's dispute of one card transaction."""

    def __init__(
        self,
        *,
        dispute_id: UUID,
        customer_id: UUID,
        transaction_id: UUID,
        reason: DisputeReason,
        description: str,
        disputed_amount: Money,
        status: DisputeStatus,
        opened_at: datetime,
        approved_amount: Money | None = None,
    ) -> None:
        """Rebuild a stored dispute, with no events. To create a new one, use Dispute.open()."""
        self._id = dispute_id
        self._customer_id = customer_id
        self._transaction_id = transaction_id
        self._reason = reason
        self._description = description
        self._disputed_amount = disputed_amount
        self._status = status
        self._opened_at = opened_at
        self._approved_amount = approved_amount
        self._events: list[DomainEvent] = []

    @classmethod
    def open(
        cls,
        *,
        customer_id: UUID,
        transaction: Transaction,
        reason: DisputeReason,
        description: str,
        disputed_amount: Money | None = None,
    ) -> Self:
        """Open a new dispute. Without disputed_amount, the whole transaction is disputed."""
        amount = transaction.amount if disputed_amount is None else disputed_amount
        if amount == Money.zero(amount.currency) or amount > transaction.amount:
            raise ValueError("disputed amount must be > 0 and <= the transaction amount")
        if not description.strip():
            raise ValueError("dispute description must not be blank")

        dispute = cls(
            dispute_id=uuid4(),
            customer_id=customer_id,
            transaction_id=transaction.id,
            reason=reason,
            description=description,
            disputed_amount=amount,
            status=DisputeStatus.OPEN,
            opened_at=datetime.now(UTC),
        )
        dispute._record(
            DisputeOpened(
                dispute_id=dispute.id,
                customer_id=customer_id,
                transaction_id=transaction.id,
                reason=reason,
                disputed_amount=amount,
            )
        )
        return dispute

    # --- read-only properties -------------------------------------------------

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def customer_id(self) -> UUID:
        return self._customer_id

    @property
    def transaction_id(self) -> UUID:
        return self._transaction_id

    @property
    def reason(self) -> DisputeReason:
        return self._reason

    @property
    def description(self) -> str:
        return self._description

    @property
    def disputed_amount(self) -> Money:
        return self._disputed_amount

    @property
    def status(self) -> DisputeStatus:
        return self._status

    @property
    def opened_at(self) -> datetime:
        return self._opened_at

    @property
    def approved_amount(self) -> Money | None:
        return self._approved_amount

    # --- commands -------------------------------------------------------------

    def start_analysis(self) -> None:
        self._move_to(DisputeStatus.UNDER_ANALYSIS)
        self._record(AnalysisStarted(dispute_id=self._id))

    def apply_proposal(self, proposal: DecisionProposal, limit: ApprovalLimit) -> None:
        """The agent proposes, the domain decides. A bad proposal goes to review, never raises."""
        # Checked up front: approved is also reachable from manual_review, so _move_to alone
        # would let a proposal decide a dispute that is waiting for a human.
        if self._status is not DisputeStatus.UNDER_ANALYSIS:
            raise InvalidTransitionError(f"cannot apply a proposal while {self._status}")

        amount = proposal.amount
        if not proposal.justification.strip():
            self.send_to_manual_review("proposal has no justification")
        elif proposal.outcome is ProposalOutcome.DENY:
            self._deny(denied_by=AGENT, reason=proposal.justification)
        elif amount is None:
            self.send_to_manual_review("approval proposal has no amount")
        elif not any(citation.strip() for citation in proposal.citations):
            self.send_to_manual_review("approval proposal cites no source")
        elif amount.currency != self._disputed_amount.currency or amount > self._disputed_amount:
            self.send_to_manual_review("proposed amount exceeds the disputed amount")
        elif limit.requires_human(amount):
            self._move_to(DisputeStatus.AWAITING_APPROVAL)
            self._record(ApprovalRequested(dispute_id=self._id, amount=amount))
        else:
            self._approve(approved_by=AGENT, amount=amount)

    def send_to_manual_review(self, reason: str) -> None:
        """Graceful degradation: also used when the LLM, RAG or the refund agent is down."""
        self._move_to(DisputeStatus.MANUAL_REVIEW)
        self._record(SentToManualReview(dispute_id=self._id, reason=reason))

    def approve(self, *, approved_by: str, amount: Money) -> None:
        """A human approves, after awaiting_approval or manual_review."""
        self._ensure_human_decision(approved_by)
        if amount == Money.zero(amount.currency) or amount > self._disputed_amount:
            raise ValueError("approved amount must be > 0 and <= the disputed amount")
        self._approve(approved_by=approved_by, amount=amount)

    def deny(self, *, denied_by: str, reason: str) -> None:
        """A human denies, after awaiting_approval or manual_review."""
        self._ensure_human_decision(denied_by)
        self._deny(denied_by=denied_by, reason=reason)

    def mark_refunded(self) -> None:
        self._ensure_can_move_to(DisputeStatus.REFUNDED)
        if self._approved_amount is None:  # only with corrupted stored data
            raise DomainError(f"dispute {self._id} has no approved amount to refund")
        self._move_to(DisputeStatus.REFUNDED)
        self._record(DisputeRefunded(dispute_id=self._id, amount=self._approved_amount))

    def mark_refund_failed(self, reason: str) -> None:
        self._move_to(DisputeStatus.REFUND_FAILED)
        self._record(RefundFailed(dispute_id=self._id, reason=reason))

    # --- events ---------------------------------------------------------------

    def pull_events(self) -> list[DomainEvent]:
        """Return the events raised since the last call, and forget them (for the outbox)."""
        events, self._events = self._events, []
        return events

    # --- internals ------------------------------------------------------------

    def _approve(self, *, approved_by: str, amount: Money) -> None:
        self._move_to(DisputeStatus.APPROVED)
        self._approved_amount = amount
        self._record(DisputeApproved(dispute_id=self._id, amount=amount, approved_by=approved_by))

    def _deny(self, *, denied_by: str, reason: str) -> None:
        self._move_to(DisputeStatus.DENIED)
        self._record(DisputeDenied(dispute_id=self._id, denied_by=denied_by, reason=reason))

    def _ensure_human_decision(self, decided_by: str) -> None:
        if self._status not in _HUMAN_DECISION_STATUSES:
            raise InvalidTransitionError(f"a human cannot decide a dispute that is {self._status}")
        if not decided_by.strip() or decided_by == AGENT:
            raise ValueError("a human decision needs the name of the person who decided")

    def _ensure_can_move_to(self, target: DisputeStatus) -> None:
        if not self._status.can_move_to(target):
            raise InvalidTransitionError(
                f"dispute {self._id} cannot move from {self._status} to {target}"
            )

    def _move_to(self, target: DisputeStatus) -> None:
        self._ensure_can_move_to(target)
        self._status = target

    def _record(self, event: DomainEvent) -> None:
        self._events.append(event)

    # --- identity -------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Dispute) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        # The description is the customer's free text and may hold personal data.
        return f"Dispute(id={self._id}, status={self._status})"
