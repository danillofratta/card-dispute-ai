"""FastAPI composition root: creates the app and includes the router of each vertical slice."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from dispute_analyst.bootstrap.dependencies import dispose_database
from dispute_analyst.features.disputes.analyze_dispute.endpoint import router as analyze_router
from dispute_analyst.features.disputes.get_dispute.endpoint import router as get_dispute_router
from dispute_analyst.features.disputes.list_queue.endpoint import router as list_queue_router
from dispute_analyst.features.disputes.open_dispute.endpoint import router as open_dispute_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Release the database connection pool when the API stops."""
    yield
    await dispose_database()


def create_app() -> FastAPI:
    """Build the API. Each slice adds its router here, and nothing else lives in this module."""
    app = FastAPI(
        title="Card Dispute Analyst",
        description="AI analyst for credit-card disputes: the agent proposes, the domain decides.",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health", tags=["Health"])
    async def health() -> dict[str, str]:
        """Report that the process is up, without touching any dependency."""
        return {"status": "ok"}

    app.include_router(open_dispute_router)
    app.include_router(list_queue_router)
    app.include_router(get_dispute_router)
    app.include_router(analyze_router)

    return app


app = create_app()
