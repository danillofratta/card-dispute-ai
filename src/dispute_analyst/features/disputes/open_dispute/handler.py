"""OpenDisputeHandler: checks the transaction with the core bank and opens the dispute."""

from dispute_analyst.application.ports.core_banking import CoreBanking
from dispute_analyst.application.ports.unit_of_work import UnitOfWork
from dispute_analyst.domain.aggregates.dispute import Dispute
from dispute_analyst.features.disputes.open_dispute.command import OpenDisputeCommand
from dispute_analyst.features.disputes.open_dispute.exceptions import TransactionNotFoundError
from dispute_analyst.features.disputes.open_dispute.result import OpenDisputeResult


class OpenDisputeHandler:
    """CQRS command handler. Knows only ports and the domain: no HTTP, no database."""

    def __init__(self, unit_of_work: UnitOfWork, core_banking: CoreBanking) -> None:
        """Receive the ports; the endpoint provides the implementations."""
        self._unit_of_work = unit_of_work
        self._core_banking = core_banking

    async def handle(self, command: OpenDisputeCommand) -> OpenDisputeResult:
        """Open the dispute and save it with its DisputeOpened event.

        Raises TransactionNotFoundError, or ValueError when the domain rejects the input.
        """
        # Calls to the core bank happen before the unit of work starts: a transaction is never
        # held open while waiting for another system.
        transaction = await self._core_banking.get_transaction(command.transaction_id)
        if transaction is None:
            raise TransactionNotFoundError(command.transaction_id)
        card = await self._core_banking.get_card(transaction.card_id)
        if card is None or card.customer_id != command.customer_id:
            raise TransactionNotFoundError(command.transaction_id)

        dispute = Dispute.open(
            customer_id=command.customer_id,
            transaction=transaction,
            reason=command.reason,
            description=command.description,
            disputed_amount=command.disputed_amount,
        )

        async with self._unit_of_work as uow:
            await uow.disputes.add(dispute)
            await uow.commit()

        return OpenDisputeResult(dispute_id=dispute.id, status=dispute.status)
