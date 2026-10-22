"""CoreBanking backed by fixed synthetic data, standing in for the bank's real API.

A real implementation is the anti-corruption layer: it calls the bank and translates its model
into our Card and Transaction, so the bank's names and formats never reach the domain.
"""

from collections.abc import Iterable
from uuid import UUID

from dispute_analyst.domain.entities.card import Card
from dispute_analyst.domain.entities.transaction import Transaction
from dispute_analyst.infrastructure.core_banking.seed import CARDS, TRANSACTIONS


class SimulatedCoreBanking:
    """Answers from a fixed list of cards and transactions."""

    def __init__(
        self,
        cards: Iterable[Card] = CARDS,
        transactions: Iterable[Transaction] = TRANSACTIONS,
    ) -> None:
        """Index the data by id. Tests can pass their own cards and transactions."""
        self._cards = {card.id: card for card in cards}
        self._transactions = {transaction.id: transaction for transaction in transactions}

    async def get_transaction(self, transaction_id: UUID) -> Transaction | None:
        """Return the transaction, or None if it is unknown."""
        return self._transactions.get(transaction_id)

    async def get_card(self, card_id: UUID) -> Card | None:
        """Return the card, or None if it is unknown."""
        return self._cards.get(card_id)
