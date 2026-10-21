from decimal import Decimal
import pytest

from dispute_analyst.domain.money import Money  

def test_creates_money_with_decimal_amount() -> None:
    money = Money(amount=Decimal("150.00"))

    assert money.amount == Decimal("150.00")
    assert money.currency == "BRL"

def test_rejects_float_amount() -> None:
    with pytest.raises(TypeError):
        Money(amount=150.00)

@pytest.mark.parametrize("amount", ["-0.01", "-100"])
def test_rejects_negative_amount(amount: str) -> None:
    with pytest.raises(ValueError):
        Money(amount=Decimal(amount))