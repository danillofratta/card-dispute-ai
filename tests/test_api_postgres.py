"""The whole API against Postgres: HTTP, slices, unit of work, repository and core bank."""

import pytest
from httpx2 import ASGITransport, AsyncClient

from dispute_analyst.bootstrap.dependencies import get_database
from dispute_analyst.infrastructure.core_banking.seed import CUSTOMER_ANA, TX_ANA_STREAMING_AGAIN
from dispute_analyst.infrastructure.persistence.sqlalchemy.database import Database
from dispute_analyst.main import create_app

pytestmark = pytest.mark.integration


async def test_open_get_and_list_a_dispute(database: Database) -> None:
    app = create_app()
    app.dependency_overrides[get_database] = lambda: database
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
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
        dispute_id = opened.json()["id"]

        details = (await client.get(f"/disputes/{dispute_id}")).json()
        queue = (await client.get("/disputes")).json()

    assert details["merchant"] == "Streaming Plus"
    assert details["disputed_amount"] == "129.90"
    assert queue["total"] == 1
    assert queue["items"][0]["id"] == dispute_id
