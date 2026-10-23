from uuid import uuid4

from fastapi.testclient import TestClient

from dispute_analyst.infrastructure.core_banking.seed import CUSTOMER_ANA, TX_ANA_STREAMING_AGAIN


def open_dispute(client: TestClient) -> str:
    response = client.post(
        "/disputes",
        json={
            "customer_id": str(CUSTOMER_ANA),
            "transaction_id": str(TX_ANA_STREAMING_AGAIN),
            "reason": "duplicate_charge",
            "description": "I was charged twice for the same subscription.",
        },
    )
    assert response.status_code == 201
    dispute_id: str = response.json()["id"]
    return dispute_id


def test_shows_the_dispute_with_merchant_and_card(client: TestClient) -> None:
    dispute_id = open_dispute(client)

    response = client.get(f"/disputes/{dispute_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "open"
    assert body["currency"] == "BRL"
    assert body["disputed_amount"] == "129.90"
    assert body["approved_amount"] is None
    assert body["merchant"] == "Streaming Plus"
    assert body["card_last_four"] == "4242"


def test_unknown_dispute_is_404(client: TestClient) -> None:
    assert client.get(f"/disputes/{uuid4()}").status_code == 404


def test_invalid_id_is_422(client: TestClient) -> None:
    assert client.get("/disputes/not-a-uuid").status_code == 422
