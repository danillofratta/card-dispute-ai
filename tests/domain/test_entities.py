from datetime import UTC, datetime
from uuid import uuid4

import pytest

from dispute_analyst.domain.entities.card import Card
from dispute_analyst.domain.entities.customer import Customer
from dispute_analyst.domain.entities.transaction import Transaction
from dispute_analyst.domain.value_objects.cpf import Cpf
from dispute_analyst.domain.value_objects.money import Money

CPF = Cpf.parse("123.456.789-09")
WHEN = datetime(2026, 10, 1, 10, tzinfo=UTC)


# --- customer ----------------------------------------------------------------


@pytest.mark.parametrize("name", ["", "   "])
def test_customer_rejects_a_blank_name(name: str) -> None:
    with pytest.raises(ValueError):
        Customer(id=uuid4(), name=name, cpf=CPF)


def test_customer_repr_hides_the_name() -> None:
    customer = Customer(id=uuid4(), name="Ana Souza", cpf=CPF)

    assert "Ana" not in repr(customer)


# --- card --------------------------------------------------------------------


@pytest.mark.parametrize("last_four", ["", "424", "42424", "42a2"])
def test_card_rejects_anything_but_four_digits(last_four: str) -> None:
    with pytest.raises(ValueError):
        Card(id=uuid4(), customer_id=uuid4(), last_four=last_four)


def test_card_masked() -> None:
    card = Card(id=uuid4(), customer_id=uuid4(), last_four="4242")

    assert card.masked() == "**** **** **** 4242"


# --- transaction -------------------------------------------------------------


def make_transaction(
    *, amount: str = "99.90", merchant: str = "Online Store", occurred_at: datetime = WHEN
) -> Transaction:
    return Transaction(
        id=uuid4(),
        card_id=uuid4(),
        amount=Money.of(amount),
        merchant=merchant,
        occurred_at=occurred_at,
    )


def test_transaction_accepts_valid_data() -> None:
    assert make_transaction().amount == Money.of("99.90")


def test_transaction_rejects_a_zero_amount() -> None:
    with pytest.raises(ValueError):
        make_transaction(amount="0")


def test_transaction_rejects_a_blank_merchant() -> None:
    with pytest.raises(ValueError):
        make_transaction(merchant="  ")


def test_transaction_rejects_a_datetime_without_time_zone() -> None:
    with pytest.raises(ValueError):
        make_transaction(occurred_at=datetime(2026, 10, 1, 10))
