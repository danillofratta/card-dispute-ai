"""UnitOfWork over Postgres: the disputes and their outbox events in one transaction."""

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from dispute_analyst.infrastructure.persistence.sqlalchemy.dispute_repository import (
    SqlAlchemyDisputeRepository,
)
from dispute_analyst.infrastructure.persistence.sqlalchemy.mappers import (
    dispute_to_model,
    event_to_outbox,
)


class SqlAlchemyUnitOfWork:
    """One session and one database transaction per `async with` block."""

    disputes: SqlAlchemyDisputeRepository

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Keep the factory; the session opens when the unit of work starts."""
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        """Open a session and a repository bound to it."""
        self._session = self._session_factory()
        self.disputes = SqlAlchemyDisputeRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Discard what was not committed and give the connection back to the pool."""
        await self.rollback()
        await self._require_session().close()

    async def commit(self) -> None:
        """Write each tracked dispute and its events, then commit them together."""
        session = self._require_session()
        for dispute in self.disputes.tracked():
            # merge inserts a new dispute or updates the row loaded in this session.
            await session.merge(dispute_to_model(dispute))
            session.add_all(event_to_outbox(event) for event in dispute.pull_events())
        await session.commit()
        self.disputes = SqlAlchemyDisputeRepository(session)

    async def rollback(self) -> None:
        """Discard every change since the last commit."""
        await self._require_session().rollback()

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("use the unit of work inside `async with`")
        return self._session
