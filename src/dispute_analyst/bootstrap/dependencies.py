"""Composition root: shared providers only. Never imports a slice (see ADR 0003).

With DATABASE_URL set, every port is backed by Postgres; without it, by memory.
"""

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from dispute_analyst.application.ports.core_banking import CoreBanking
from dispute_analyst.application.ports.unit_of_work import UnitOfWork
from dispute_analyst.bootstrap.settings import get_settings
from dispute_analyst.domain.repositories.dispute_repository import DisputeRepository
from dispute_analyst.infrastructure.core_banking.simulated_core_banking import (
    SimulatedCoreBanking,
)
from dispute_analyst.infrastructure.core_banking.sqlalchemy_core_banking import (
    SqlAlchemyCoreBanking,
)
from dispute_analyst.infrastructure.persistence.memory.dispute_repository import (
    InMemoryDisputeRepository,
)
from dispute_analyst.infrastructure.persistence.memory.store import InMemoryStore
from dispute_analyst.infrastructure.persistence.memory.unit_of_work import InMemoryUnitOfWork
from dispute_analyst.infrastructure.persistence.sqlalchemy.database import Database
from dispute_analyst.infrastructure.persistence.sqlalchemy.dispute_repository import (
    SqlAlchemyDisputeRepository,
)
from dispute_analyst.infrastructure.persistence.sqlalchemy.unit_of_work import (
    SqlAlchemyUnitOfWork,
)


@lru_cache
def get_database() -> Database | None:
    """One database (and connection pool) per process, or None to keep data in memory."""
    url = get_settings().database_url
    return None if url is None else Database(url)


async def dispose_database() -> None:
    """Close the connection pool on shutdown, if one was ever opened."""
    if get_database.cache_info().currsize == 0:
        return
    database = get_database()
    if database is not None:
        await database.dispose()
    get_database.cache_clear()


@lru_cache
def get_store() -> InMemoryStore:
    """One store per process: the in-memory stand-in for the database."""
    return InMemoryStore()


@lru_cache
def _simulated_core_banking() -> SimulatedCoreBanking:
    return SimulatedCoreBanking()


DatabaseDependency = Annotated[Database | None, Depends(get_database)]
StoreDependency = Annotated[InMemoryStore, Depends(get_store)]


def get_core_banking(database: DatabaseDependency) -> CoreBanking:
    """The core bank: its schema in Postgres, or fixed synthetic data in memory."""
    if database is None:
        return _simulated_core_banking()
    return SqlAlchemyCoreBanking(database.session_factory)


def get_unit_of_work(database: DatabaseDependency, store: StoreDependency) -> UnitOfWork:
    """A new unit of work for each request."""
    if database is None:
        return InMemoryUnitOfWork(store)
    return SqlAlchemyUnitOfWork(database.session_factory)


async def get_dispute_repository(
    database: DatabaseDependency, store: StoreDependency
) -> AsyncIterator[DisputeRepository]:
    """A repository for queries. With Postgres, its session closes when the request ends."""
    if database is None:
        yield InMemoryDisputeRepository(store)
        return
    async with database.session_factory() as session:
        yield SqlAlchemyDisputeRepository(session)


# Endpoints depend on these aliases: they see only the port types, never the implementations.
UnitOfWorkDependency = Annotated[UnitOfWork, Depends(get_unit_of_work)]
CoreBankingDependency = Annotated[CoreBanking, Depends(get_core_banking)]
DisputeRepositoryDependency = Annotated[DisputeRepository, Depends(get_dispute_repository)]
