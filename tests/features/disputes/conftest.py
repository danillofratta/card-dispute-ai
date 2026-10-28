"""Fixtures shared by the endpoint tests of the disputes slices."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from dispute_analyst.bootstrap.dependencies import get_database, get_store
from dispute_analyst.infrastructure.persistence.memory.store import InMemoryStore
from dispute_analyst.main import create_app


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def client(store: InMemoryStore) -> Iterator[TestClient]:
    """An app in memory with a fresh store, even when a local .env sets DATABASE_URL."""
    app = create_app()
    app.dependency_overrides[get_database] = lambda: None
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app) as client:
        yield client
