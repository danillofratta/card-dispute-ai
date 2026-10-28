"""Fixtures shared by the endpoint tests of the disputes slices."""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dispute_analyst.bootstrap.dependencies import get_database, get_store
from dispute_analyst.infrastructure.persistence.memory.store import InMemoryStore
from dispute_analyst.main import create_app


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def app(store: InMemoryStore) -> FastAPI:
    """An app in memory with a fresh store, even when a local .env sets DATABASE_URL.

    Tests can add their own dependency_overrides to it before using the client.
    """
    app = create_app()
    app.dependency_overrides[get_database] = lambda: None
    app.dependency_overrides[get_store] = lambda: store
    return app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client
