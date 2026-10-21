"""Customer: the card holder, as known to the core bank."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from dispute_analyst.domain.value_objects.cpf import Cpf


@dataclass(frozen=True, slots=True)
class Customer:
    """Read-only snapshot of a customer. The name stays out of repr to keep it out of logs."""

    id: UUID
    name: str = field(repr=False)
    cpf: Cpf

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("customer name must not be blank")
