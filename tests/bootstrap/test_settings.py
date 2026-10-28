from decimal import Decimal

import pytest
from pydantic import ValidationError

from dispute_analyst.bootstrap.settings import Settings


def test_without_database_url_data_stays_in_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert Settings(_env_file=None).database_url is None


def test_reads_database_url_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    url = "postgresql+asyncpg://dispute:dispute@localhost:5432/disputes"
    monkeypatch.setenv("DATABASE_URL", url)

    assert Settings(_env_file=None).database_url == url


def test_the_approval_limit_defaults_to_the_one_the_dataset_expects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APPROVAL_LIMIT", raising=False)

    assert Settings(_env_file=None).approval_limit == Decimal("500.00")


def test_reads_the_approval_limit_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPROVAL_LIMIT", "750.50")

    assert Settings(_env_file=None).approval_limit == Decimal("750.50")


@pytest.mark.parametrize("limit", ["-1", "12.345", "abc"])
def test_an_invalid_approval_limit_fails_at_startup(
    monkeypatch: pytest.MonkeyPatch, limit: str
) -> None:
    monkeypatch.setenv("APPROVAL_LIMIT", limit)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
