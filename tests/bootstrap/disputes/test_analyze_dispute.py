from collections.abc import Iterator

import pytest

from dispute_analyst.bootstrap.disputes.analyze_dispute import (
    get_approval_limit,
    get_dispute_analyzer,
)
from dispute_analyst.bootstrap.settings import get_settings
from dispute_analyst.domain.value_objects.money import Money
from dispute_analyst.infrastructure.agents.unavailable_analyzer import UnavailableAnalyzer


@pytest.fixture(autouse=True)
def fresh_settings() -> Iterator[None]:
    """get_settings() is cached: clear it so each test reads its own environment."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_without_a_model_the_analyzer_is_unavailable() -> None:
    assert isinstance(get_dispute_analyzer(), UnavailableAnalyzer)


def test_the_approval_limit_comes_from_the_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPROVAL_LIMIT", "750.50")

    limit = get_approval_limit()

    assert limit.value == Money.of("750.50")
    assert limit.requires_human(Money.of("750.51"))
    assert not limit.requires_human(Money.of("750.50"))
