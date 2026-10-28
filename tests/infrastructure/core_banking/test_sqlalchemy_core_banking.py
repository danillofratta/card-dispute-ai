from datetime import UTC, datetime
from uuid import uuid4

import pytest

from dispute_analyst.domain.value_objects.money import Money
from dispute_analyst.infrastructure.core_banking.seed import (
    CARD_ANA,
    CUSTOMER_ANA,
    TX_ANA_STREAMING,
    TX_ANA_STREAMING_AGAIN,
)
from dispute_analyst.infrastructure.core_banking.sqlalchemy_core_banking import (
    SqlAlchemyCoreBanking,
)
from dispute_analyst.infrastructure.persistence.sqlalchemy.database import Database

pytestmark = pytest.mark.integration


async def test_translates_rows_into_domain_objects(database: Database) -> None:
    bank = SqlAlchemyCoreBanking(database.session_factory)

    transaction = await bank.get_transaction(TX_ANA_STREAMING_AGAIN)
    card = await bank.get_card(CARD_ANA)

    assert transaction is not None
    assert transaction.amount == Money.of("129.90")
    assert transaction.merchant == "Streaming Plus"
    assert transaction.occurred_at.utcoffset() is not None
    assert card is not None
    assert card.customer_id == CUSTOMER_ANA
    assert card.last_four == "4242"


async def test_unknown_ids_are_none(database: Database) -> None:
    bank = SqlAlchemyCoreBanking(database.session_factory)

    assert await bank.get_transaction(uuid4()) is None
    assert await bank.get_card(uuid4()) is None


async def test_lists_the_card_history_in_the_window_oldest_first(database: Database) -> None:
    bank = SqlAlchemyCoreBanking(database.session_factory)
    october_5 = datetime(2026, 10, 5, tzinfo=UTC)

    whole_day = await bank.list_card_transactions(
        CARD_ANA, since=october_5, until=datetime(2026, 10, 6, tzinfo=UTC)
    )
    before_the_second = await bank.list_card_transactions(
        CARD_ANA, since=october_5, until=datetime(2026, 10, 5, 9, 1, tzinfo=UTC)
    )

    assert [t.id for t in whole_day] == [TX_ANA_STREAMING, TX_ANA_STREAMING_AGAIN]
    assert whole_day[0].amount == Money.of("129.90")
    assert [t.id for t in before_the_second] == [TX_ANA_STREAMING]
