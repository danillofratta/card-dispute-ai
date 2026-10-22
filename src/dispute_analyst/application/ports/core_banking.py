"""CoreBanking: the bank's system of record for cards and transactions, another bounded context."""

from typing import Protocol
from uuid import UUID

from dispute_analyst.domain.entities.card import Card
from dispute_analyst.domain.entities.transaction import Transaction


class CoreBanking(Protocol):
    """Core Banking system interface for interacting with banking operations."""

    async def get_transaction(self, transaction_id: UUID) -> Transaction | None:
        """Retrieve a transaction by its ID, or return None if not found."""

    async def get_card(self, card_id: UUID) -> Card | None:
        """Retrieve a card by its ID, or return None if not found."""
