from types import TracebackType
from typing import Protocol, Self

from dispute_analyst.domain.repositories.dispute_repository import DisputeRepository


class UnitOfWork(Protocol):
    """Unit of Work pattern for managing transactional operations on repositories."""

    @property
    def disputes(self) -> DisputeRepository:
        """Access the dispute repository."""

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None:
        """Commit the current transaction."""

    async def rollback(self) -> None:
        """Rollback the current transaction."""
