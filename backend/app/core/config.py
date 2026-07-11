# app/core/config.py

"""
Centralized application configuration.

Loads settings from environment variables or a .env file
using pydantic-settings.

A cached singleton instance is exposed through
get_settings() to avoid repeated parsing.
"""

from functools import lru_cache
from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # =========================
    # Project
    # =========================
    PROJECT_NAME: str = "SentinelGraph AI"
    API_DESCRIPTION: str = "Digital Public Safety Intelligence Platform"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # =========================
    # Security
    # =========================
    SECRET_KEY: SecretStr

    # =========================
    # Database (PostgreSQL)
    # =========================
    DATABASE_HOST: str
    DATABASE_PORT: int = Field(default=5432, ge=1, le=65535)
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PASSWORD: SecretStr

    DB_POOL_SIZE: int = Field(default=10, ge=1)
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0)
    DB_POOL_TIMEOUT: int = Field(default=30, ge=0)
    DB_POOL_RECYCLE: int = Field(default=1800, ge=-1)

    # =========================
    # Neo4j Graph Database
    # =========================
    NEO4J_URI: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: SecretStr
    NEO4J_DATABASE: str = "neo4j"

    # =========================
    # AI / LLM Settings
    # =========================
    GEMINI_API_KEY: SecretStr
    GEMINI_MODEL: str = "gemini-flash-latest"
    LLM_TEMPERATURE: float = Field(default=0.2, ge=0.0, le=2.0)
    LLM_MAX_TOKENS: int = Field(default=2048, ge=1)

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """
        Constructs the async PostgreSQL URL for SQLAlchemy.
        """
        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD.get_secret_value()}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @computed_field
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """
        Constructs the synchronous PostgreSQL URL for Alembic.
        Uses psycopg2 driver for migration compatibility.
        """
        return (
            f"postgresql+psycopg2://{self.DATABASE_USER}:{self.DATABASE_PASSWORD.get_secret_value()}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached instance of the Settings class.
    """
    return Settings()


settings = get_settings()
