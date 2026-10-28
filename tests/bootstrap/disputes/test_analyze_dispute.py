from collections.abc import Iterator

import pytest

from dispute_analyst.bootstrap.disputes.analyze_dispute import (
    get_approval_limit,
    get_dispute_analyzer,
    get_merchants,
)
from dispute_analyst.bootstrap.settings import Settings, get_settings
from dispute_analyst.domain.value_objects.money import Money
from dispute_analyst.infrastructure.agents.baseline.analyzer import BaselineAnalyzer
from dispute_analyst.infrastructure.agents.unavailable_analyzer import UnavailableAnalyzer
from dispute_analyst.infrastructure.core_banking.simulated_core_banking import (
    SimulatedCoreBanking,
)
from dispute_analyst.infrastructure.merchants.simulated_merchants import SimulatedMerchants


@pytest.fixture(autouse=True)
def fresh_settings() -> Iterator[None]:
    """get_settings() is cached: clear it so each test reads its own environment."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def settings(**values: str) -> Settings:
    """Settings from these values only: no .env, so a developer's real key never leaks in."""
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


def analyzer_for(config: Settings) -> object:
    return get_dispute_analyzer(config, SimulatedCoreBanking(), SimulatedMerchants())


def test_without_a_model_the_analyzer_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    assert isinstance(analyzer_for(settings()), UnavailableAnalyzer)


def test_with_a_model_the_baseline_agent_analyzes() -> None:
    groq = settings(
        llm_provider="openai",
        llm_model="openai/gpt-oss-120b",
        llm_base_url="https://api.groq.com/openai/v1",
        llm_api_key="gsk-test",
    )

    assert isinstance(analyzer_for(groq), BaselineAnalyzer)


def test_in_memory_the_merchants_are_simulated() -> None:
    assert isinstance(get_merchants(None), SimulatedMerchants)


def test_the_approval_limit_comes_from_the_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPROVAL_LIMIT", "750.50")

    limit = get_approval_limit()

    assert limit.value == Money.of("750.50")
    assert limit.requires_human(Money.of("750.51"))
    assert not limit.requires_human(Money.of("750.50"))
