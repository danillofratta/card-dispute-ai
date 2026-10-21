import dataclasses
from decimal import Decimal

import pytest

from dispute_analyst.domain.value_objects.money import Money

# --- creation and validation -------------------------------------------------


def test_creates_money_with_decimal_amount() -> None:
    money = Money(Decimal("150.00"))

    assert money.amount == Decimal("150.00")
    assert money.currency == "BRL"


def test_accepts_zero() -> None:
    assert Money(Decimal("0")).amount == Decimal("0")


def test_rejects_float_amount() -> None:
    with pytest.raises(TypeError):
        Money(150.0)  # type: ignore[arg-type]


@pytest.mark.parametrize("amount", ["-0.01", "-100", "NaN", "Infinity", "-Infinity", "10.001"])
def test_rejects_invalid_amount(amount: str) -> None:
    with pytest.raises(ValueError):
        Money(Decimal(amount))


@pytest.mark.parametrize("amount", ["10", "10.5", "10.100"])
def test_accepts_up_to_two_decimal_places(amount: str) -> None:
    Money(Decimal(amount))


@pytest.mark.parametrize("currency", ["brl", "BR", "BRLL", "R$", "ÇÃO"])
def test_rejects_invalid_currency(currency: str) -> None:
    with pytest.raises(ValueError):
        Money(Decimal("1"), currency)


def test_is_immutable() -> None:
    money = Money.of("1")

    with pytest.raises(dataclasses.FrozenInstanceError):
        money.amount = Decimal("2")  # type: ignore[misc]


def test_equality_is_by_value() -> None:
    assert Money(Decimal("10")) == Money(Decimal("10.00"))


# --- factories ---------------------------------------------------------------


def test_of_builds_from_a_string() -> None:
    assert Money.of("150.00") == Money(Decimal("150.00"))


def test_of_rejects_text_that_is_not_a_number() -> None:
    with pytest.raises(ValueError):
        Money.of("abc")


def test_of_rejects_float() -> None:
    with pytest.raises(TypeError):
        Money.of(1.5)  # type: ignore[arg-type]


def test_zero() -> None:
    assert Money.zero() == Money.of("0")


# --- arithmetic and comparison -----------------------------------------------


def test_adds_and_subtracts() -> None:
    assert Money.of("100.50") + Money.of("20") == Money.of("120.50")
    assert Money.of("100.50") - Money.of("20") == Money.of("80.50")


def test_subtraction_cannot_go_negative() -> None:
    with pytest.raises(ValueError):
        _ = Money.of("20") - Money.of("100")


def test_compares_amounts_in_the_same_currency() -> None:
    small, big = Money.of("1"), Money.of("2")

    assert small < big
    assert small <= big
    assert big > small
    assert big >= small


def test_rejects_operations_across_currencies() -> None:
    brl, usd = Money.of("1"), Money.of("1", "USD")

    with pytest.raises(ValueError):
        _ = brl + usd
    with pytest.raises(ValueError):
        _ = brl - usd
    with pytest.raises(ValueError):
        _ = brl < usd


def test_rejects_operations_with_other_types() -> None:
    with pytest.raises(TypeError):
        _ = Money.of("1") + 5  # type: ignore[operator]


def test_str_shows_currency_and_two_decimals() -> None:
    assert str(Money.of("120.5")) == "BRL 120.50"
