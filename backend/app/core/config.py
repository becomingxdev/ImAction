import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings for ImAction CKA.
    Loads values from environment variables and fallback '.env' file.
    On Google Cloud Run, all sensitive values are injected as env vars —
    no .env file is present. GOOGLE_CLOUD_PROJECT triggers Vertex AI ADC auth.
    """
    # Core Application Configurations
    APP_NAME: str = "ImAction"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "super-secret-key-change-me-in-production"

    # Provider Configurations
    # "gemini" uses real Gemini/Vertex AI. "mock" is local dev only.
    EMBEDDING_PROVIDER: str = "gemini"
    LLM_PROVIDER: str = "gemini"

    # Gemini / Vertex AI
    GEMINI_API_KEY: Optional[str] = None          # Only needed if NOT on GCP
    GOOGLE_CLOUD_PROJECT: Optional[str] = None    # Set on Cloud Run → uses ADC
    GOOGLE_CLOUD_LOCATION: str = "us-central1"
    GEMINI_MODEL: str = "gemini-2.5-flash"         # Gemini 2.5 Flash on Vertex AI

    # CORS — comma-separated list supported via env var
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # PostgreSQL Configurations
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "imaction_cka"

    # Database connection strings (optional full-URL overrides)
    DATABASE_URL: Optional[str] = None
    ASYNC_DATABASE_URL: Optional[str] = None

    @property
    def sync_database_url(self) -> str:
        """Dynamically constructs the sync DB URL or normalises postgres:// prefix."""
        if self.DATABASE_URL:
            if self.DATABASE_URL.startswith("postgres://"):
                return self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
            return self.DATABASE_URL
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def async_database_url(self) -> str:
        """Dynamically constructs the async DB URL."""
        if self.ASYNC_DATABASE_URL:
            return self.ASYNC_DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Instantiate settings singleton
settings = Settings()
