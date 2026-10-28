from datetime import UTC, datetime
from uuid import uuid4

from dispute_analyst.infrastructure.core_banking.seed import (
    CARD_ANA,
    CUSTOMER_ANA,
    TX_ANA_ONLINE_STORE,
    TX_ANA_STREAMING,
    TX_ANA_STREAMING_AGAIN,
)
from dispute_analyst.infrastructure.core_banking.simulated_core_banking import (
    SimulatedCoreBanking,
)

OCTOBER_5 = datetime(2026, 10, 5, tzinfo=UTC)
OCTOBER_6 = datetime(2026, 10, 6, tzinfo=UTC)


async def test_finds_a_seeded_transaction_and_its_card() -> None:
    bank = SimulatedCoreBanking()

    transaction = await bank.get_transaction(TX_ANA_ONLINE_STORE)
    assert transaction is not None
    card = await bank.get_card(transaction.card_id)

    assert card is not None
    assert card.id == CARD_ANA
    assert card.customer_id == CUSTOMER_ANA


async def test_returns_none_for_unknown_ids() -> None:
    bank = SimulatedCoreBanking()

    assert await bank.get_transaction(uuid4()) is None
    assert await bank.get_card(uuid4()) is None


async def test_accepts_custom_data() -> None:
    bank = SimulatedCoreBanking(cards=[], transactions=[])

    assert await bank.get_transaction(TX_ANA_ONLINE_STORE) is None


async def test_lists_the_card_history_in_the_window_oldest_first() -> None:
    bank = SimulatedCoreBanking()

    history = await bank.list_card_transactions(CARD_ANA, since=OCTOBER_5, until=OCTOBER_6)

    # The online store charge on October 1st is outside the window.
    assert [t.id for t in history] == [TX_ANA_STREAMING, TX_ANA_STREAMING_AGAIN]


async def test_the_history_window_excludes_until() -> None:
    bank = SimulatedCoreBanking()
    second_charge = datetime(2026, 10, 5, 9, 1, tzinfo=UTC)

    history = await bank.list_card_transactions(CARD_ANA, since=OCTOBER_5, until=second_charge)

    assert [t.id for t in history] == [TX_ANA_STREAMING]


async def test_an_unknown_card_has_no_history() -> None:
    bank = SimulatedCoreBanking()

    assert await bank.list_card_transactions(uuid4(), since=OCTOBER_5, until=OCTOBER_6) == []
