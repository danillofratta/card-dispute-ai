from uuid import UUID, uuid4

import pytest

from dispute_analyst.domain.aggregates.dispute import Dispute
from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.domain.enums.proposal_outcome import ProposalOutcome
from dispute_analyst.domain.events.dispute_event import (
    AnalysisStarted,
    DisputeApproved,
    SentToManualReview,
)
from dispute_analyst.domain.exceptions import InvalidTransitionError
from dispute_analyst.domain.value_objects.approval_limit import ApprovalLimit
from dispute_analyst.domain.value_objects.decision_proposal import DecisionProposal
from dispute_analyst.domain.value_objects.money import Money
from dispute_analyst.features.disputes.analyze_dispute.command import AnalyzeDisputeCommand
from dispute_analyst.features.disputes.analyze_dispute.exceptions import (
    AnalyzeDisputeNotFoundError,
    AnalyzeDisputeUnavailableError,
)
from dispute_analyst.features.disputes.analyze_dispute.gateway import (
    DisputeCaseDto,
)
from dispute_analyst.features.disputes.analyze_dispute.handler import AnalyzeDisputeHandler
from dispute_analyst.features.disputes.analyze_dispute.result import AnalyzeDisputeResult
from dispute_analyst.infrastructure.core_banking.seed import (
    CUSTOMER_ANA,
    CUSTOMER_BRUNO,
    TRANSACTIONS,
    TX_ANA_STREAMING,
    TX_ANA_STREAMING_AGAIN,
    TX_BRUNO_ELECTRONICS,
)
from dispute_analyst.infrastructure.persistence.memory.store import InMemoryStore
from dispute_analyst.infrastructure.persistence.memory.unit_of_work import InMemoryUnitOfWork

LIMIT = ApprovalLimit(Money.of("500.00"))
CITATION = f"transaction:{TX_ANA_STREAMING}"


class FakeAnalyzer:
    """Returns a fixed proposal, or fails. Records what it was asked and what was saved."""

    def __init__(
        self, store: InMemoryStore, proposal: DecisionProposal | None = None, error: str = ""
    ) -> None:
        self._store = store
        self._proposal = proposal
        self._error = error
        self.cases: list[DisputeCaseDto] = []
        self.saved_status: DisputeStatus | None = None

    async def analyze(self, case: DisputeCaseDto) -> DecisionProposal:
        self.cases.append(case)
        # What is already committed while the model "thinks": proves step 1 did not wait.
        self.saved_status = self._store.disputes[case.dispute_id].status
        if self._proposal is None:
            raise AnalyzeDisputeUnavailableError(self._error)
        return self._proposal


def approve(amount: str, citations: tuple[str, ...] = (CITATION,)) -> DecisionProposal:
    return DecisionProposal(
        outcome=ProposalOutcome.APPROVE,
        justification="Same card, merchant and amount one minute apart: a duplicate charge.",
        citations=citations,
        amount=Money.of(amount),
    )


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


async def open_dispute(
    store: InMemoryStore,
    customer_id: UUID = CUSTOMER_ANA,
    transaction_id: UUID = TX_ANA_STREAMING_AGAIN,
) -> UUID:
    transaction = next(t for t in TRANSACTIONS if t.id == transaction_id)
    dispute = Dispute.open(
        customer_id=customer_id,
        transaction=transaction,
        reason=DisputeReason.DUPLICATE_CHARGE,
        description="Fui cobrado duas vezes pela mesma assinatura.",
    )
    async with InMemoryUnitOfWork(store) as uow:
        await uow.disputes.add(dispute)
        await uow.commit()
    store.outbox.clear()  # keep only the events of the analysis
    return dispute.id


async def analyze(
    store: InMemoryStore, analyzer: FakeAnalyzer, dispute_id: UUID
) -> AnalyzeDisputeResult:
    handler = AnalyzeDisputeHandler(InMemoryUnitOfWork(store), analyzer, LIMIT)
    return await handler.handle(AnalyzeDisputeCommand(dispute_id=dispute_id))


async def test_a_good_proposal_below_the_limit_is_approved(store: InMemoryStore) -> None:
    dispute_id = await open_dispute(store)
    proposal = approve("129.90")

    result = await analyze(store, FakeAnalyzer(store, proposal), dispute_id)

    assert result.status is DisputeStatus.APPROVED
    assert result.proposal == proposal
    assert result.failure is None
    assert store.disputes[dispute_id].approved_amount == Money.of("129.90")
    assert [type(event) for event in store.outbox] == [AnalysisStarted, DisputeApproved]


async def test_above_the_limit_a_human_decides(store: InMemoryStore) -> None:
    dispute_id = await open_dispute(store, CUSTOMER_BRUNO, TX_BRUNO_ELECTRONICS)
    analyzer = FakeAnalyzer(store, approve("2450.00", citations=("order:no-delivery-proof",)))

    result = await analyze(store, analyzer, dispute_id)

    assert result.status is DisputeStatus.AWAITING_APPROVAL


async def test_a_denial_is_saved(store: InMemoryStore) -> None:
    dispute_id = await open_dispute(store)
    deny = DecisionProposal(ProposalOutcome.DENY, "Two separate purchases, days apart.")

    await analyze(store, FakeAnalyzer(store, deny), dispute_id)

    assert store.disputes[dispute_id].status is DisputeStatus.DENIED


async def test_a_proposal_without_citations_goes_to_manual_review(store: InMemoryStore) -> None:
    dispute_id = await open_dispute(store)

    result = await analyze(store, FakeAnalyzer(store, approve("129.90", citations=())), dispute_id)

    assert result.status is DisputeStatus.MANUAL_REVIEW


async def test_an_unavailable_analyzer_sends_the_dispute_to_manual_review(
    store: InMemoryStore,
) -> None:
    dispute_id = await open_dispute(store)

    result = await analyze(store, FakeAnalyzer(store, error="model timed out"), dispute_id)

    assert result.status is DisputeStatus.MANUAL_REVIEW
    assert result.proposal is None
    assert result.failure == "model timed out"
    [_, review] = store.outbox
    assert isinstance(review, SentToManualReview)
    assert review.reason == "analysis unavailable: model timed out"


async def test_the_dispute_is_saved_under_analysis_before_the_model_runs(
    store: InMemoryStore,
) -> None:
    dispute_id = await open_dispute(store)
    analyzer = FakeAnalyzer(store, approve("129.90"))

    await analyze(store, analyzer, dispute_id)

    assert analyzer.saved_status is DisputeStatus.UNDER_ANALYSIS


async def test_the_analyzer_gets_a_read_only_case_not_the_aggregate(store: InMemoryStore) -> None:
    dispute_id = await open_dispute(store)
    analyzer = FakeAnalyzer(store, approve("129.90"))

    await analyze(store, analyzer, dispute_id)

    [case] = analyzer.cases
    assert isinstance(case, DisputeCaseDto)
    assert case.dispute_id == dispute_id
    assert case.transaction_id == TX_ANA_STREAMING_AGAIN
    assert case.disputed_amount == Money.of("129.90")


async def test_unknown_dispute(store: InMemoryStore) -> None:
    analyzer = FakeAnalyzer(store, approve("129.90"))

    with pytest.raises(AnalyzeDisputeNotFoundError):
        await analyze(store, analyzer, uuid4())

    assert analyzer.cases == []


async def test_a_dispute_is_analyzed_only_once(store: InMemoryStore) -> None:
    dispute_id = await open_dispute(store)
    await analyze(store, FakeAnalyzer(store, approve("129.90")), dispute_id)
    again = FakeAnalyzer(store, approve("129.90"))

    with pytest.raises(InvalidTransitionError):
        await analyze(store, again, dispute_id)

    assert again.cases == []
    assert store.disputes[dispute_id].status is DisputeStatus.APPROVED
