import pytest
from fastapi.testclient import TestClient

from dispute_analyst.infrastructure.core_banking.seed import (
    CUSTOMER_ANA,
    CUSTOMER_BRUNO,
    TX_ANA_STREAMING_AGAIN,
    TX_BRUNO_FOOD,
)


def open_dispute(client: TestClient, customer: str, transaction: str) -> str:
    response = client.post(
        "/disputes",
        json={
            "customer_id": customer,
            "transaction_id": transaction,
            "reason": "duplicate_charge",
            "description": "Charged twice.",
        },
    )
    assert response.status_code == 201
    dispute_id: str = response.json()["id"]
    return dispute_id


def test_empty_queue(client: TestClient) -> None:
    response = client.get("/disputes")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_queue_is_oldest_first(client: TestClient) -> None:
    first = open_dispute(client, str(CUSTOMER_ANA), str(TX_ANA_STREAMING_AGAIN))
    second = open_dispute(client, str(CUSTOMER_BRUNO), str(TX_BRUNO_FOOD))

    body = client.get("/disputes").json()

    assert [item["id"] for item in body["items"]] == [first, second]
    assert body["items"][0]["disputed_amount"] == "129.90"
    assert body["total"] == 2


def test_queue_is_paginated(client: TestClient) -> None:
    open_dispute(client, str(CUSTOMER_ANA), str(TX_ANA_STREAMING_AGAIN))
    second = open_dispute(client, str(CUSTOMER_BRUNO), str(TX_BRUNO_FOOD))

    body = client.get("/disputes", params={"limit": 1, "offset": 1}).json()

    assert [item["id"] for item in body["items"]] == [second]
    assert body["total"] == 2


def test_queue_filters_by_status(client: TestClient) -> None:
    open_dispute(client, str(CUSTOMER_ANA), str(TX_ANA_STREAMING_AGAIN))

    assert client.get("/disputes", params={"status": "open"}).json()["total"] == 1
    assert client.get("/disputes", params={"status": "manual_review"}).json()["total"] == 0


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"status": "lost"}],
    ids=["limit-zero", "limit-too-big", "negative-offset", "unknown-status"],
)
def test_invalid_parameters_are_422(client: TestClient, params: dict[str, object]) -> None:
    assert client.get("/disputes", params=params).status_code == 422
