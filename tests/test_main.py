from fastapi.testclient import TestClient

from dispute_analyst.main import create_app


def test_health() -> None:
    cliente = TestClient(create_app())

    response = cliente.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
