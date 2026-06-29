from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Global application configuration.

    Loads values from the .env file and environment variables.
    """

    # =====================================================
    # Project Information
    # =====================================================

    PROJECT_NAME: str = "SentinelGraph AI"
    API_TITLE: str = "SentinelGraph AI API"
    API_DESCRIPTION: str = (
        "AI-powered Digital Public Safety Intelligence Platform."
    )

    VERSION: str = "0.1.0"

    API_V1_PREFIX: str = "/api/v1"

    ENVIRONMENT: str = "development"

    DEBUG: bool = True

    # =====================================================
    # Security
    # =====================================================

    SECRET_KEY: str

    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # =====================================================
    # Database
    # =====================================================

    DATABASE_URL: str

    # =====================================================
    # Neo4j
    # =====================================================

    NEO4J_URI: str

    NEO4J_USERNAME: str

    NEO4J_PASSWORD: str

    # =====================================================
    # AI Providers
    # =====================================================

    LLM_PROVIDER: str = "gemini"

    GEMINI_API_KEY: str

    OPENAI_API_KEY: str = ""

    GROQ_API_KEY: str = ""

    # =====================================================
    # CORS
    # =====================================================

    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    # =====================================================
    # Pydantic Configuration
    # =====================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    """
    return Settings()


settings = get_settings()