import pytest
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from dispute_analyst.infrastructure.llm.chat_models import LlmConfig, Provider, build_chat_model

GROQ = "https://api.groq.com/openai/v1"


@pytest.mark.parametrize(
    ("provider", "model_class"),
    [("openai", ChatOpenAI), ("anthropic", ChatAnthropic), ("ollama", ChatOllama)],
)
def test_builds_the_configured_provider(provider: Provider, model_class: type) -> None:
    model = build_chat_model(LlmConfig(provider, "some-model", api_key="key"))

    assert isinstance(model, model_class)


def test_an_openai_compatible_api_such_as_groq() -> None:
    config = LlmConfig("openai", "openai/gpt-oss-120b", base_url=GROQ, api_key="gsk-test")

    model = build_chat_model(config)

    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "openai/gpt-oss-120b"
    assert model.openai_api_base == GROQ
    assert model.temperature == 0


def test_the_api_key_never_shows_in_repr() -> None:
    config = LlmConfig("openai", "gpt", api_key="sk-very-secret")

    assert "sk-very-secret" not in repr(config)
    assert "sk-very-secret" not in repr(build_chat_model(config))
