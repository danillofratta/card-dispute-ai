from decimal import Decimal

import pytest
from pydantic import ValidationError

from dispute_analyst.bootstrap.settings import Settings

LLM_VARIABLES = ("LLM_PROVIDER", "LLM_MODEL", "LLM_BASE_URL", "LLM_API_KEY")


@pytest.fixture
def no_llm_in_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in LLM_VARIABLES:
        monkeypatch.delenv(name, raising=False)


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


@pytest.mark.usefixtures("no_llm_in_the_environment")
def test_without_a_provider_there_is_no_model() -> None:
    assert Settings(_env_file=None).llm_provider is None


@pytest.mark.usefixtures("no_llm_in_the_environment")
def test_reads_groq_as_an_openai_compatible_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "openai/gpt-oss-120b")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("LLM_API_KEY", "gsk-test")

    settings = Settings(_env_file=None)

    assert settings.llm_model == "openai/gpt-oss-120b"
    assert settings.llm_api_key is not None
    assert settings.llm_api_key.get_secret_value() == "gsk-test"
    assert "gsk-test" not in repr(settings)


@pytest.mark.usefixtures("no_llm_in_the_environment")
@pytest.mark.parametrize(
    "llm",
    [
        pytest.param({"llm_provider": "openai", "llm_api_key": "key"}, id="no model"),
        pytest.param({"llm_provider": "openai", "llm_model": "gpt"}, id="openai without key"),
        pytest.param({"llm_provider": "anthropic", "llm_model": "claude"}, id="anthropic no key"),
        pytest.param({"llm_provider": "gemini", "llm_model": "x"}, id="unknown provider"),
    ],
)
def test_an_incomplete_llm_fails_at_startup(llm: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **llm)  # type: ignore[arg-type]


@pytest.mark.usefixtures("no_llm_in_the_environment")
def test_a_local_model_needs_no_key() -> None:
    settings = Settings(_env_file=None, llm_provider="ollama", llm_model="qwen3:8b")

    assert settings.llm_api_key is None
