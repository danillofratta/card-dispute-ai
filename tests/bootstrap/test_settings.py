import pytest

from dispute_analyst.bootstrap.settings import Settings


def test_without_database_url_data_stays_in_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert Settings(_env_file=None).database_url is None


def test_reads_database_url_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    url = "postgresql+asyncpg://dispute:dispute@localhost:5432/disputes"
    monkeypatch.setenv("DATABASE_URL", url)

    assert Settings(_env_file=None).database_url == url
