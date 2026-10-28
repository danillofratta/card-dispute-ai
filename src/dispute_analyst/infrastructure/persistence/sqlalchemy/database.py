"""Database: the SQLAlchemy engine and session factory for Postgres."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class Database:
    """Owns the engine and its connection pool. Create one per process, not per request."""

    def __init__(self, url: str) -> None:
        """Connect lazily: the pool opens a connection only when a session needs one."""
        self.engine = create_async_engine(url, pool_pre_ping=True)
        # expire_on_commit=False: objects stay readable after commit without new queries.
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False
        )

    async def dispose(self) -> None:
        """Close every pooled connection, on shutdown."""
        await self.engine.dispose()
