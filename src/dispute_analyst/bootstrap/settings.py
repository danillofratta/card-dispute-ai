"""Settings read from environment variables, or from a local .env file in development."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration of the running process. Each field maps to an upper-case variable."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # postgresql+asyncpg://user:password@host:5432/database. Without it, data stays in memory.
    database_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Read the settings from environment variables or a .env file."""
    return Settings()
