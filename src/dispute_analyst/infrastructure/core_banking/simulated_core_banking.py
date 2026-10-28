"""CoreBanking backed by fixed synthetic data, standing in for the bank's real API.

A real implementation is the anti-corruption layer: it calls the bank and translates its model
into our Card and Transaction, so the bank's names and formats never reach the domain.
"""

from collections.abc import Iterable
from datetime import datetime
from operator import attrgetter
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

    async def list_card_transactions(
        self, card_id: UUID, *, since: datetime, until: datetime
    ) -> list[Transaction]:
        """Return the card's charges with since <= occurred_at < until, oldest first."""
        found = (
            transaction
            for transaction in self._transactions.values()
            if transaction.card_id == card_id and since <= transaction.occurred_at < until
        )
        return sorted(found, key=attrgetter("occurred_at"))
