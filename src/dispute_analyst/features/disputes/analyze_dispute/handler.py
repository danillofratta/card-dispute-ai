"""AnalyzeDisputeHandler: the agent proposes, the domain decides."""

from uuid import UUID

from dispute_analyst.application.ports.unit_of_work import UnitOfWork
from dispute_analyst.domain.aggregates.dispute import Dispute
from dispute_analyst.domain.value_objects.approval_limit import ApprovalLimit
from dispute_analyst.domain.value_objects.decision_proposal import DecisionProposal
from dispute_analyst.features.disputes.analyze_dispute.command import AnalyzeDisputeCommand
from dispute_analyst.features.disputes.analyze_dispute.exceptions import (
    AnalyzeDisputeNotFoundError,
    AnalyzeDisputeUnavailableError,
)
from dispute_analyst.features.disputes.analyze_dispute.gateway import (
    AnalyzeDisputeGateway,
    DisputeCaseDto,
)
from dispute_analyst.features.disputes.analyze_dispute.result import AnalyzeDisputeResult


class AnalyzeDisputeHandler:
    """CQRS command handler. Two short transactions, with the analysis between them."""

    def __init__(
        self, unit_of_work: UnitOfWork, analyzer: AnalyzeDisputeGateway, limit: ApprovalLimit
    ) -> None:
        """Receive the ports and the limit; the endpoint provides them."""
        self._unit_of_work = unit_of_work
        self._analyzer = analyzer
        self._limit = limit

    async def handle(self, command: AnalyzeDisputeCommand) -> AnalyzeDisputeResult:
        """Analyze an open dispute and save the decision with its events.

        Raises AnalyzeDisputeNotFoundError, or InvalidTransitionError if the dispute is not open.
        """
        # 1. Mark the dispute as under analysis and commit, before calling the model: no
        #    database transaction stays open while the model thinks for seconds.
        async with self._unit_of_work as uow:
            dispute = await self._load(uow, command.dispute_id)
            dispute.start_analysis()
            await uow.commit()
        case = DisputeCaseDto(
            dispute_id=dispute.id,
            transaction_id=dispute.transaction_id,
            reason=dispute.reason,
            description=dispute.description,
            disputed_amount=dispute.disputed_amount,
        )

        # 2. The analysis, outside any transaction. A failure is an answer, not an error.
        proposal: DecisionProposal | None = None
        failure: str | None = None
        try:
            proposal = await self._analyzer.analyze(case)
        except AnalyzeDisputeUnavailableError as error:
            failure = str(error)

        # 3. The domain decides, in a second transaction.
        async with self._unit_of_work as uow:
            dispute = await self._load(uow, command.dispute_id)
            if proposal is None:
                dispute.send_to_manual_review(f"analysis unavailable: {failure}")
            else:
                dispute.apply_proposal(proposal, self._limit)
            await uow.commit()

        return AnalyzeDisputeResult(
            dispute_id=dispute.id, status=dispute.status, proposal=proposal, failure=failure
        )

    @staticmethod
    async def _load(uow: UnitOfWork, dispute_id: UUID) -> Dispute:
        dispute = await uow.disputes.get_by_id(dispute_id)
        if dispute is None:
            raise AnalyzeDisputeNotFoundError(dispute_id)
        return dispute
