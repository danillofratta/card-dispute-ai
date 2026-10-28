"""Fixtures for the integration tests against a real Postgres (`pytest -m integration`)."""

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text

from dispute_analyst.infrastructure.core_banking.seed import (
    CARDS,
    CUSTOMER_ANA,
    CUSTOMER_BRUNO,
    TRANSACTIONS,
)
from dispute_analyst.infrastructure.persistence.sqlalchemy.database import Database
from dispute_analyst.infrastructure.persistence.sqlalchemy.models import (
    CardModel,
    CustomerModel,
    TransactionModel,
)

TABLES = "outbox, disputes, core_banking.transactions, core_banking.cards, core_banking.customers"


@pytest.fixture
async def database() -> AsyncIterator[Database]:
    """A migrated Postgres, emptied and loaded with the seed bank data before each test.

    Needs TEST_DATABASE_URL pointing to a database migrated with `alembic upgrade head`.
    Every test empties it: never point it at a database whose data you want to keep.
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if url is None:
        pytest.skip("set TEST_DATABASE_URL to run the Postgres integration tests")

    database = Database(url)
    async with database.session_factory() as session:
        await session.execute(text(f"TRUNCATE {TABLES}"))
        session.add_all(
            [
                CustomerModel(id=CUSTOMER_ANA, name="Ana Souza", cpf="52998224725"),
                CustomerModel(id=CUSTOMER_BRUNO, name="Bruno Lima", cpf="11144477735"),
            ]
        )
        await session.flush()
        session.add_all(
            CardModel(id=card.id, customer_id=card.customer_id, last_four=card.last_four)
            for card in CARDS
        )
        await session.flush()
        session.add_all(
            TransactionModel(
                id=transaction.id,
                card_id=transaction.card_id,
                amount=transaction.amount.amount,
                currency=transaction.amount.currency,
                merchant=transaction.merchant,
                occurred_at=transaction.occurred_at,
            )
            for transaction in TRANSACTIONS
        )
        await session.commit()

    yield database
    await database.dispose()
