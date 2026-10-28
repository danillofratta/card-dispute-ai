"""The whole API against Postgres: HTTP, slices, unit of work, repository and core bank."""

from collections.abc import AsyncIterator

import pytest
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy import select

from dispute_analyst.bootstrap.dependencies import get_database
from dispute_analyst.bootstrap.disputes.analyze_dispute import get_dispute_analyzer
from dispute_analyst.domain.enums.proposal_outcome import ProposalOutcome
from dispute_analyst.domain.value_objects.decision_proposal import DecisionProposal
from dispute_analyst.features.disputes.analyze_dispute.gateway import DisputeCaseDto
from dispute_analyst.infrastructure.core_banking.seed import (
    CUSTOMER_ANA,
    TX_ANA_STREAMING,
    TX_ANA_STREAMING_AGAIN,
)
from dispute_analyst.infrastructure.persistence.sqlalchemy.database import Database
from dispute_analyst.infrastructure.persistence.sqlalchemy.models import OutboxEventModel
from dispute_analyst.main import create_app

pytestmark = pytest.mark.integration


class ApprovingAnalyzer:
    """Approves the whole disputed amount, citing the twin charge."""

    async def analyze(self, case: DisputeCaseDto) -> DecisionProposal:
        return DecisionProposal(
            outcome=ProposalOutcome.APPROVE,
            justification="Same card, merchant and amount one minute apart.",
            citations=(f"transaction:{TX_ANA_STREAMING}",),
            amount=case.disputed_amount,
        )


@pytest.fixture
async def client(database: Database) -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_database] = lambda: database
    app.dependency_overrides[get_dispute_analyzer] = ApprovingAnalyzer
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def open_dispute(client: AsyncClient) -> str:
    opened = await client.post(
        "/disputes",
        json={
            "customer_id": str(CUSTOMER_ANA),
            "transaction_id": str(TX_ANA_STREAMING_AGAIN),
            "reason": "duplicate_charge",
            "description": "I was charged twice for the same subscription.",
        },
    )
    assert opened.status_code == 201
    dispute_id: str = opened.json()["id"]
    return dispute_id


async def test_open_get_and_list_a_dispute(client: AsyncClient) -> None:
    dispute_id = await open_dispute(client)

    details = (await client.get(f"/disputes/{dispute_id}")).json()
    queue = (await client.get("/disputes")).json()

    assert details["merchant"] == "Streaming Plus"
    assert details["disputed_amount"] == "129.90"
    assert queue["total"] == 1
    assert queue["items"][0]["id"] == dispute_id


async def test_analyze_a_dispute_in_two_transactions(
    client: AsyncClient, database: Database
) -> None:
    dispute_id = await open_dispute(client)

    analysis = await client.post(f"/disputes/{dispute_id}/analysis")
    details = (await client.get(f"/disputes/{dispute_id}")).json()

    assert analysis.status_code == 200
    assert analysis.json()["status"] == "approved"
    assert details["status"] == "approved"
    assert details["approved_amount"] == "129.90"
    async with database.session_factory() as session:
        events = await session.scalars(
            select(OutboxEventModel.event_type).order_by(OutboxEventModel.occurred_at)
        )
        assert list(events) == ["DisputeOpened", "AnalysisStarted", "DisputeApproved"]
