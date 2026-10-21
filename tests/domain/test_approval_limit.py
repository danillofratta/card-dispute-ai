from decimal import Decimal

import pytest

from dispute_analyst.domain.value_objects.approval_limit import ApprovalLimit
from dispute_analyst.domain.value_objects.money import Money

LIMIT = ApprovalLimit(Money.of("500"))


@pytest.mark.parametrize(
    ("amount", "expected"),
    [("499.99", False), ("500", False), ("500.01", True)],
)
def test_requires_human_only_above_the_limit(amount: str, expected: bool) -> None:
    assert LIMIT.requires_human(Money.of(amount)) is expected


def test_rejects_another_currency() -> None:
    with pytest.raises(ValueError):
        LIMIT.requires_human(Money.of("1", "USD"))


def test_value_must_be_money() -> None:
    with pytest.raises(TypeError):
        ApprovalLimit(Decimal("500"))  # type: ignore[arg-type]
