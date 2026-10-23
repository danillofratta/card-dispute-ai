"""GetDisputeHandler: loads one dispute and adds what the bank knows about its transaction."""

from dispute_analyst.application.ports.core_banking import CoreBanking
from dispute_analyst.domain.repositories.dispute_repository import DisputeRepository
from dispute_analyst.features.disputes.get_dispute.query import GetDisputeQuery
from dispute_analyst.features.disputes.get_dispute.result import GetDisputeResult


class GetDisputeHandler:
    """CQRS query handler. Reads the aggregate through the repository and never changes it."""

    def __init__(self, disputes: DisputeRepository, core_banking: CoreBanking) -> None:
        """Receive the ports; the endpoint provides the implementations."""
        self._disputes = disputes
        self._core_banking = core_banking

    async def handle(self, query: GetDisputeQuery) -> GetDisputeResult | None:
        """Return the dispute's details, or None if it does not exist."""
        dispute = await self._disputes.get_by_id(query.dispute_id)
        if dispute is None:
            return None

        # The aggregate keeps only the transaction id; the bank has the merchant and the card.
        transaction = await self._core_banking.get_transaction(dispute.transaction_id)
        card = None
        if transaction is not None:
            card = await self._core_banking.get_card(transaction.card_id)

        return GetDisputeResult(
            id=dispute.id,
            customer_id=dispute.customer_id,
            transaction_id=dispute.transaction_id,
            status=dispute.status,
            reason=dispute.reason,
            description=dispute.description,
            disputed_amount=dispute.disputed_amount,
            approved_amount=dispute.approved_amount,
            opened_at=dispute.opened_at,
            merchant=None if transaction is None else transaction.merchant,
            card_last_four=None if card is None else card.last_four,
        )
