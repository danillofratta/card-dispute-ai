"""Synthetic cards and transactions for the simulated core bank. No real person or card."""

from datetime import UTC, datetime
from uuid import UUID

from dispute_analyst.domain.entities.card import Card
from dispute_analyst.domain.entities.transaction import Transaction
from dispute_analyst.domain.value_objects.money import Money

# Fixed, readable ids, so they can be typed into Swagger.
CUSTOMER_ANA = UUID("00000000-0000-0000-0000-000000000001")
CUSTOMER_BRUNO = UUID("00000000-0000-0000-0000-000000000002")

CARD_ANA = UUID("00000000-0000-0000-0000-000000000101")
CARD_BRUNO = UUID("00000000-0000-0000-0000-000000000102")

TX_ANA_ONLINE_STORE = UUID("00000000-0000-0000-0000-000000001001")
TX_ANA_STREAMING = UUID("00000000-0000-0000-0000-000000001002")
TX_ANA_STREAMING_AGAIN = UUID("00000000-0000-0000-0000-000000001003")
TX_BRUNO_ELECTRONICS = UUID("00000000-0000-0000-0000-000000001004")
TX_BRUNO_FOOD = UUID("00000000-0000-0000-0000-000000001005")

CARDS = (
    Card(id=CARD_ANA, customer_id=CUSTOMER_ANA, last_four="4242"),
    Card(id=CARD_BRUNO, customer_id=CUSTOMER_BRUNO, last_four="1881"),
)


def _at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=UTC)


TRANSACTIONS = (
    Transaction(TX_ANA_ONLINE_STORE, CARD_ANA, Money.of("800.00"), "Online Store", _at(1, 14)),
    # Charged twice, one minute apart: the classic duplicate charge.
    Transaction(TX_ANA_STREAMING, CARD_ANA, Money.of("129.90"), "Streaming Plus", _at(5, 9)),
    Transaction(
        TX_ANA_STREAMING_AGAIN, CARD_ANA, Money.of("129.90"), "Streaming Plus", _at(5, 9, 1)
    ),
    # Above the approval limit: will need a human.
    Transaction(
        TX_BRUNO_ELECTRONICS, CARD_BRUNO, Money.of("2450.00"), "Electronics Hub", _at(8, 19)
    ),
    Transaction(TX_BRUNO_FOOD, CARD_BRUNO, Money.of("59.90"), "Food Delivery", _at(12, 21)),
)
