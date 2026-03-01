"""
Settings loaded from .env. Never hardcode credentials.
App and Alembic use sync SQLAlchemy with psycopg2.
"""
import os
from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    database_url: str = Field(default="", validation_alias="DATABASE_URL")
    google_maps_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_MAPS_API_KEY", "GOOGLE_API_KEY"),
    )
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    secret_key: str = Field(default="", validation_alias="SECRET_KEY")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def _normalized_url(self) -> str:
        """Base URL with standard postgresql scheme (no +driver)."""
        url = self.database_url or os.getenv("DATABASE_URL", "")
        if "postgresql+asyncpg://" in url:
            return url.replace("postgresql+asyncpg://", "postgresql://", 1)
        if "postgresql+psycopg2://" in url:
            return url.replace("postgresql+psycopg2://", "postgresql://", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        """URL for app/Alembic: postgresql+psycopg2 (sync)."""
        base = self._normalized_url()
        if not base.startswith("postgresql://"):
            return base
        return base.replace("postgresql://", "postgresql+psycopg2://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
