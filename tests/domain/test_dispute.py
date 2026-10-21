from datetime import UTC, datetime
from uuid import uuid4

import pytest

from dispute_analyst.domain.aggregates.dispute import AGENT, Dispute
from dispute_analyst.domain.entities.transaction import Transaction
from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.domain.enums.proposal_outcome import ProposalOutcome
from dispute_analyst.domain.events.dispute_event import (
    ApprovalRequested,
    DisputeApproved,
    DisputeDenied,
    DisputeOpened,
    DisputeRefunded,
    SentToManualReview,
)
from dispute_analyst.domain.events.domain_event import DomainEvent
from dispute_analyst.domain.exceptions import InvalidTransitionError
from dispute_analyst.domain.value_objects.approval_limit import ApprovalLimit
from dispute_analyst.domain.value_objects.decision_proposal import DecisionProposal
from dispute_analyst.domain.value_objects.money import Money

LIMIT = ApprovalLimit(Money.of("500"))
CITED = ("Internal dispute policy, section 4.2",)
APPROVE = ProposalOutcome.APPROVE
DENY = ProposalOutcome.DENY


def make_transaction() -> Transaction:
    return Transaction(
        id=uuid4(),
        card_id=uuid4(),
        amount=Money.of("800"),
        merchant="Online Store",
        occurred_at=datetime(2026, 10, 1, 10, tzinfo=UTC),
    )


def open_dispute(
    *, disputed_amount: Money | None = None, description: str = "I was charged twice."
) -> Dispute:
    return Dispute.open(
        customer_id=uuid4(),
        transaction=make_transaction(),
        reason=DisputeReason.DUPLICATE_CHARGE,
        description=description,
        disputed_amount=disputed_amount,
    )


def approve(amount: str) -> DecisionProposal:
    return DecisionProposal(APPROVE, "Duplicate charge confirmed.", CITED, Money.of(amount))


@pytest.fixture
def dispute() -> Dispute:
    """A dispute under analysis, with its earlier events already pulled."""
    dispute = open_dispute()
    dispute.start_analysis()
    dispute.pull_events()
    return dispute


@pytest.fixture
def approved(dispute: Dispute) -> Dispute:
    """A dispute approved by the agent for BRL 300."""
    dispute.apply_proposal(approve("300"), LIMIT)
    dispute.pull_events()
    return dispute


# --- state machine -----------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "target", "allowed"),
    [
        (DisputeStatus.OPEN, DisputeStatus.UNDER_ANALYSIS, True),
        (DisputeStatus.OPEN, DisputeStatus.APPROVED, False),
        (DisputeStatus.MANUAL_REVIEW, DisputeStatus.APPROVED, True),
        (DisputeStatus.REFUND_FAILED, DisputeStatus.REFUNDED, True),
        (DisputeStatus.APPROVED, DisputeStatus.DENIED, False),
    ],
)
def test_state_machine(source: DisputeStatus, target: DisputeStatus, allowed: bool) -> None:
    assert source.can_move_to(target) is allowed


@pytest.mark.parametrize("final", [DisputeStatus.DENIED, DisputeStatus.REFUNDED])
@pytest.mark.parametrize("target", list(DisputeStatus))
def test_final_statuses_go_nowhere(final: DisputeStatus, target: DisputeStatus) -> None:
    assert not final.can_move_to(target)


# --- opening -----------------------------------------------------------------


def test_open_starts_open_with_one_event() -> None:
    dispute = open_dispute()

    assert dispute.status is DisputeStatus.OPEN
    [event] = dispute.pull_events()
    assert isinstance(event, DisputeOpened)
    assert event.dispute_id == dispute.id


def test_open_disputes_the_whole_transaction_by_default() -> None:
    assert open_dispute().disputed_amount == Money.of("800")


def test_open_accepts_a_partial_amount() -> None:
    assert open_dispute(disputed_amount=Money.of("200")).disputed_amount == Money.of("200")


@pytest.mark.parametrize("amount", ["0", "800.01"])
def test_open_rejects_an_amount_out_of_range(amount: str) -> None:
    with pytest.raises(ValueError):
        open_dispute(disputed_amount=Money.of(amount))


def test_open_rejects_a_blank_description() -> None:
    with pytest.raises(ValueError):
        open_dispute(description="   ")


def test_cannot_start_analysis_twice(dispute: Dispute) -> None:
    with pytest.raises(InvalidTransitionError):
        dispute.start_analysis()


# --- the agent proposes, the domain decides ----------------------------------


@pytest.mark.parametrize(
    ("proposal", "expected_status", "expected_event"),
    [
        pytest.param(
            approve("300"), DisputeStatus.APPROVED, DisputeApproved, id="approve-below-limit"
        ),
        pytest.param(
            approve("600"),
            DisputeStatus.AWAITING_APPROVAL,
            ApprovalRequested,
            id="above-limit-needs-a-human",
        ),
        pytest.param(
            DecisionProposal(APPROVE, "Duplicate.", (), Money.of("300")),
            DisputeStatus.MANUAL_REVIEW,
            SentToManualReview,
            id="no-citation",
        ),
        pytest.param(
            approve("900"), DisputeStatus.MANUAL_REVIEW, SentToManualReview, id="above-disputed"
        ),
        pytest.param(
            DecisionProposal(APPROVE, "Duplicate.", CITED, Money.of("300", "USD")),
            DisputeStatus.MANUAL_REVIEW,
            SentToManualReview,
            id="other-currency",
        ),
        pytest.param(
            DecisionProposal(APPROVE, "Duplicate.", CITED),
            DisputeStatus.MANUAL_REVIEW,
            SentToManualReview,
            id="no-amount",
        ),
        pytest.param(
            DecisionProposal(DENY, "The customer made the purchase."),
            DisputeStatus.DENIED,
            DisputeDenied,
            id="deny",
        ),
        pytest.param(
            DecisionProposal(DENY, "   "),
            DisputeStatus.MANUAL_REVIEW,
            SentToManualReview,
            id="blank-justification",
        ),
    ],
)
def test_apply_proposal(
    dispute: Dispute,
    proposal: DecisionProposal,
    expected_status: DisputeStatus,
    expected_event: type[DomainEvent],
) -> None:
    dispute.apply_proposal(proposal, LIMIT)

    assert dispute.status is expected_status
    [event] = dispute.pull_events()
    assert isinstance(event, expected_event)


def test_a_proposal_cannot_decide_a_dispute_waiting_for_a_human(dispute: Dispute) -> None:
    dispute.send_to_manual_review("LLM unavailable")

    with pytest.raises(InvalidTransitionError):
        dispute.apply_proposal(approve("300"), LIMIT)


# --- human decisions ---------------------------------------------------------


def test_a_human_approves_after_an_approval_request(dispute: Dispute) -> None:
    dispute.apply_proposal(approve("600"), LIMIT)

    dispute.approve(approved_by="maria.silva", amount=Money.of("600"))

    assert dispute.status is DisputeStatus.APPROVED
    assert dispute.approved_amount == Money.of("600")


def test_a_human_denies_after_manual_review(dispute: Dispute) -> None:
    dispute.send_to_manual_review("LLM unavailable")

    dispute.deny(denied_by="maria.silva", reason="Purchase confirmed by the merchant.")

    assert dispute.status is DisputeStatus.DENIED


def test_a_human_cannot_decide_while_under_analysis(dispute: Dispute) -> None:
    with pytest.raises(InvalidTransitionError):
        dispute.approve(approved_by="maria.silva", amount=Money.of("100"))


@pytest.mark.parametrize("approver", ["", "   ", AGENT])
def test_a_human_decision_needs_a_person(dispute: Dispute, approver: str) -> None:
    dispute.send_to_manual_review("LLM unavailable")

    with pytest.raises(ValueError):
        dispute.approve(approved_by=approver, amount=Money.of("100"))


def test_a_human_cannot_approve_more_than_disputed(dispute: Dispute) -> None:
    dispute.send_to_manual_review("LLM unavailable")

    with pytest.raises(ValueError):
        dispute.approve(approved_by="maria.silva", amount=Money.of("900"))


# --- refund ------------------------------------------------------------------


def test_refund_succeeds(approved: Dispute) -> None:
    approved.mark_refunded()

    assert approved.status is DisputeStatus.REFUNDED
    [event] = approved.pull_events()
    assert isinstance(event, DisputeRefunded)
    assert event.amount == Money.of("300")


def test_refund_can_be_retried_after_a_failure(approved: Dispute) -> None:
    approved.mark_refund_failed("refund agent timed out")
    approved.mark_refunded()

    assert approved.status is DisputeStatus.REFUNDED


def test_a_failed_refund_can_go_to_manual_review(approved: Dispute) -> None:
    approved.mark_refund_failed("refund agent timed out")
    approved.send_to_manual_review("refund keeps failing")

    assert approved.status is DisputeStatus.MANUAL_REVIEW


def test_cannot_refund_before_approval(dispute: Dispute) -> None:
    with pytest.raises(InvalidTransitionError):
        dispute.mark_refunded()


# --- events and identity -----------------------------------------------------


def test_pull_events_empties_the_list() -> None:
    dispute = open_dispute()

    assert len(dispute.pull_events()) == 1
    assert dispute.pull_events() == []


def test_two_disputes_are_never_equal() -> None:
    assert open_dispute() != open_dispute()


def test_repr_hides_the_customer_text() -> None:
    dispute = open_dispute(description="Call me at 99999-0000")

    assert "99999" not in repr(dispute)
