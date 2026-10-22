"""FastAPI composition root: creates the app and includes the router of each vertical slice."""

from fastapi import FastAPI

from dispute_analyst.features.disputes.open_dispute.endpoint import router as open_dispute_router


def create_app() -> FastAPI:
    """Build the API. Each slice adds its router here, and nothing else lives in this module."""
    app = FastAPI(
        title="Card Dispute Analyst",
        description="AI analyst for credit-card disputes: the agent proposes, the domain decides.",
        version="0.1.0",
    )

    @app.get("/health", tags=["Health"])
    async def health() -> dict[str, str]:
        """Report that the process is up, without touching any dependency."""
        return {"status": "ok"}

    app.include_router(open_dispute_router)

    return app


app = create_app()
