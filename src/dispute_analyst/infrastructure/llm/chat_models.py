"""The chat model, chosen by configuration: OpenAI (or any compatible API), Anthropic or Ollama.

LangChain's BaseChatModel is the common interface of the three, so the agents never know which
provider answers. There is no LLM port of our own on top of it (ADR 0006).
"""

from dataclasses import dataclass, field
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

type Provider = Literal["openai", "anthropic", "ollama"]


@dataclass(frozen=True, slots=True)
class LlmConfig:
    """Which model to call and how. The key stays out of repr, so it never reaches a log."""

    provider: Provider
    model: str
    base_url: str | None = None
    api_key: str | None = field(default=None, repr=False)
    timeout_seconds: float = 60


def build_chat_model(config: LlmConfig) -> BaseChatModel:
    """Create the provider's chat model. Temperature 0: the same case should get the same answer."""
    api_key = SecretStr(config.api_key or "")
    match config.provider:
        case "openai":
            return ChatOpenAI(
                model=config.model,
                base_url=config.base_url,
                api_key=api_key,
                temperature=0,
                timeout=config.timeout_seconds,
                max_retries=2,
            )
        case "anthropic":
            return ChatAnthropic(
                model_name=config.model,
                base_url=config.base_url,
                api_key=api_key,
                temperature=0,
                timeout=config.timeout_seconds,
                max_retries=2,
                stop=None,  # has a default, but its type stubs make mypy ask for it
            )
        case "ollama":
            return ChatOllama(
                model=config.model,
                base_url=config.base_url,
                temperature=0,
                client_kwargs={"timeout": config.timeout_seconds},
            )
