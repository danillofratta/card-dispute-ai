"""ApprovalLimit value object: above it, a human must approve the decision."""

from __future__ import annotations

from dataclasses import dataclass

from dispute_analyst.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class ApprovalLimit:
    """The highest amount the system may approve without a human."""

    value: Money

    def __post_init__(self) -> None:
        if not isinstance(self.value, Money):
            raise TypeError(f"value must be Money, got {type(self.value).__name__}")

    def requires_human(self, amount: Money) -> bool:
        """True when approving this amount needs a human. Currencies must match."""
        return amount > self.value
