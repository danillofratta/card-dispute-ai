"""Settings read from environment variables, or from a local .env file in development."""

from decimal import Decimal
from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration of the running process. Each field maps to an upper-case variable."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # postgresql+asyncpg://user:password@host:5432/database. Without it, data stays in memory.
    database_url: str | None = None

    # In BRL: approvals above it wait for a human. The evals dataset expects 500.00.
    approval_limit: Decimal = Field(default=Decimal("500.00"), ge=0, decimal_places=2)

    # The analysis model. Without LLM_PROVIDER, every analysis goes to manual review.
    # "openai" also serves any OpenAI-compatible API, such as Groq, through LLM_BASE_URL.
    llm_provider: Literal["openai", "anthropic", "ollama"] | None = None
    llm_model: str | None = None
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = None
    # The whole analysis, every model call and tool included, must finish within this.
    llm_timeout_seconds: float = Field(default=60, gt=0)

    # Tracing in Langfuse. Without the keys, nothing is traced.
    langfuse_public_key: str | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: str = "http://localhost:3000"

    @model_validator(mode="after")
    def _llm_is_complete(self) -> Self:
        """Fail at startup, not in the middle of an analysis."""
        if self.llm_provider is None:
            return self
        if not self.llm_model:
            raise ValueError("LLM_MODEL is required when LLM_PROVIDER is set")
        if self.llm_provider != "ollama" and self.llm_api_key is None:
            raise ValueError(f"LLM_API_KEY is required for LLM_PROVIDER={self.llm_provider}")
        return self


@lru_cache
def get_settings() -> Settings:
    """Read the settings from environment variables or a .env file."""
    return Settings()
