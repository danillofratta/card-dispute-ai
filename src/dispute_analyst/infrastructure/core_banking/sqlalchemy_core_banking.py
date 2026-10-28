"""CoreBanking over the core_banking schema in Postgres.

This is the anti-corruption layer: it reads the bank's tables and translates each row into our
Card and Transaction, so the bank's names and formats never reach the domain.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from dispute_analyst.domain.entities.card import Card
from dispute_analyst.domain.entities.transaction import Transaction
from dispute_analyst.domain.value_objects.money import Money
from dispute_analyst.infrastructure.persistence.sqlalchemy.models import CardModel, TransactionModel


class SqlAlchemyCoreBanking:
    """Each call uses its own short session: reading the bank never joins our transactions."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_transaction(self, transaction_id: UUID) -> Transaction | None:
        """Return the transaction, or None if the bank does not know it."""
        async with self._session_factory() as session:
            row = await session.get(TransactionModel, transaction_id)
        return None if row is None else _to_transaction(row)

    async def get_card(self, card_id: UUID) -> Card | None:
        """Return the card, or None if the bank does not know it."""
        async with self._session_factory() as session:
            row = await session.get(CardModel, card_id)
        if row is None:
            return None
        return Card(id=row.id, customer_id=row.customer_id, last_four=row.last_four)

    async def list_card_transactions(
        self, card_id: UUID, *, since: datetime, until: datetime
    ) -> list[Transaction]:
        """Return the card's charges with since <= occurred_at < until, oldest first."""
        statement = (
            select(TransactionModel)
            .where(
                TransactionModel.card_id == card_id,
                TransactionModel.occurred_at >= since,
                TransactionModel.occurred_at < until,
            )
            .order_by(TransactionModel.occurred_at)
        )
        async with self._session_factory() as session:
            rows = await session.scalars(statement)
            return [_to_transaction(row) for row in rows]


def _to_transaction(row: TransactionModel) -> Transaction:
    """Translate the bank's row into our Transaction."""
    return Transaction(
        id=row.id,
        card_id=row.card_id,
        amount=Money(row.amount, row.currency),
        merchant=row.merchant,
        occurred_at=row.occurred_at,
    )
