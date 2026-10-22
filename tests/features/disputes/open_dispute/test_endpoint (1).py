from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from dispute_analyst.bootstrap.dependencies import get_store
from dispute_analyst.infrastructure.core_banking.seed import (
    CUSTOMER_ANA,
    CUSTOMER_BRUNO,
    TX_ANA_STREAMING_AGAIN,
)
from dispute_analyst.infrastructure.persistence.memory.store import InMemoryStore
from dispute_analyst.main import create_app


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def client(store: InMemoryStore) -> Iterator[TestClient]:
    """An app whose store is fresh for every test, instead of the process-wide one."""
    app = create_app()
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app) as client:
        yield client


def body(**changes: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "customer_id": str(CUSTOMER_ANA),
        "transaction_id": str(TX_ANA_STREAMING_AGAIN),
        "reason": "duplicate_charge",
        "description": "I was charged twice for the same subscription.",
    }
    values.update(changes)
    return values


def test_opens_a_dispute(client: TestClient, store: InMemoryStore) -> None:
    response = client.post("/disputes", json=body(disputed_amount="129.90"))

    assert response.status_code == 201
    assert response.json()["status"] == "open"
    assert len(store.disputes) == 1


def test_someone_elses_transaction_is_404(client: TestClient) -> None:
    response = client.post("/disputes", json=body(customer_id=str(CUSTOMER_BRUNO)))

    assert response.status_code == 404


@pytest.mark.parametrize("amount", ["12.345", "abc", "-1", "1,50", 129.9])
def test_amount_must_be_text_with_up_to_two_decimals(client: TestClient, amount: Any) -> None:
    response = client.post("/disputes", json=body(disputed_amount=amount))

    assert response.status_code == 422


@pytest.mark.parametrize(
    "changes",
    [
        {"reason": "chargeback"},
        {"description": ""},
        {"description": "   "},
        {"disputed_amount": "500.00"},
        {"customer_id": "not-a-uuid"},
    ],
    ids=["unknown-reason", "empty-description", "blank-description", "above-transaction", "bad-id"],
)
def test_invalid_disputes_are_422(client: TestClient, changes: dict[str, Any]) -> None:
    response = client.post("/disputes", json=body(**changes))

    assert response.status_code == 422
