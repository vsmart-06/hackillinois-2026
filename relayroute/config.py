"""
Settings loaded from .env. Never hardcode credentials.
App and Alembic use sync SQLAlchemy with psycopg2.
"""
import os
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root (parent of relayroute package) so .env is found regardless of cwd
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings from environment variables and .env."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(default="", validation_alias="DATABASE_URL")
    db_host: str = Field(default="localhost", validation_alias="DB_HOST")
    db_port: int = Field(default=5432, validation_alias="DB_PORT")
    db_user: str = Field(default="", validation_alias="DB_USER")
    db_password: str = Field(default="", validation_alias="DB_PASSWORD")
    db_name: str = Field(default="relayroute", validation_alias="DB_NAME")

    google_maps_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_MAPS_API_KEY", "GOOGLE_API_KEY"),
    )
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    secret_key: str = Field(default="", validation_alias="SECRET_KEY")

    def _normalized_url(self) -> str:
        """Base URL with standard postgresql scheme (no +driver)."""
        url = self.database_url or os.getenv("DATABASE_URL", "")
        if "postgresql+asyncpg://" in url:
            return url.replace("postgresql+asyncpg://", "postgresql://", 1)
        if "postgresql+psycopg2://" in url:
            return url.replace("postgresql+psycopg2://", "postgresql://", 1)
        return url

    def _built_url(self) -> str:
        """Build postgresql URL from DB_* components. Special chars in password must be URL-encoded."""
        from urllib.parse import quote_plus

        user = self.db_user or "postgres"
        password = quote_plus(self.db_password) if self.db_password else ""
        auth = f"{user}:{password}" if password else user
        return f"postgresql://{auth}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def sync_database_url(self) -> str:
        """URL for app/Alembic: postgresql+psycopg2 (sync). Uses DATABASE_URL or builds from DB_*."""
        base = self._normalized_url()
        if not base or not base.strip():
            base = self._built_url()
        if not base.startswith("postgresql://"):
            return base
        return base.replace("postgresql://", "postgresql+psycopg2://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
