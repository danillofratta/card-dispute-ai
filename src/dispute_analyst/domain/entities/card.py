"""Card: a payment card that belongs to a customer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

_LAST_FOUR = re.compile(r"[0-9]{4}")


@dataclass(frozen=True, slots=True)
class Card:
    """Read-only snapshot of a card. Only the last four digits are ever stored."""

    id: UUID
    customer_id: UUID
    last_four: str

    def __post_init__(self) -> None:
        if not _LAST_FOUR.fullmatch(self.last_four):
            raise ValueError("last_four must be exactly 4 digits")

    def masked(self) -> str:
        return f"**** **** **** {self.last_four}"