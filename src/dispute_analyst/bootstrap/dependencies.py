"""Composition root: shared providers only. Never imports a slice (see ADR 0003)."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from dispute_analyst.application.ports.core_banking import CoreBanking
from dispute_analyst.application.ports.unit_of_work import UnitOfWork
from dispute_analyst.infrastructure.core_banking.simulated_core_banking import (
    SimulatedCoreBanking,
)
from dispute_analyst.infrastructure.persistence.memory.store import InMemoryStore
from dispute_analyst.infrastructure.persistence.memory.unit_of_work import InMemoryUnitOfWork


@lru_cache
def get_store() -> InMemoryStore:
    """One store per process: the in-memory stand-in for the database."""
    return InMemoryStore()


@lru_cache
def get_core_banking() -> CoreBanking:
    """One simulated core bank per process."""
    return SimulatedCoreBanking()


def get_unit_of_work(store: Annotated[InMemoryStore, Depends(get_store)]) -> UnitOfWork:
    """A new unit of work for each request, over the shared store."""
    return InMemoryUnitOfWork(store)


# Endpoints depend on these aliases: they see only the port types, never the implementations.
UnitOfWorkDependency = Annotated[UnitOfWork, Depends(get_unit_of_work)]
CoreBankingDependency = Annotated[CoreBanking, Depends(get_core_banking)]
