"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:3000"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/stock_analyze"

    # LLM API Keys
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Data Sources
    FINMIND_TOKEN: Optional[str] = None
    FRED_API_KEY: Optional[str] = None

    # Auth / JWT
    JWT_SECRET: str = "dev-insecure-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days

    # LLM Settings
    LLM_DEFAULT_TEMPERATURE: float = 0.3
    LLM_MAX_RETRIES: int = 2

    # Scheduler
    SCHEDULER_ENABLED: bool = True

    @property
    def async_database_url(self) -> str:
        """Normalise the DB URL to the asyncpg driver.

        Hosts like Railway/Heroku provide ``postgres://`` or ``postgresql://``;
        SQLAlchemy's async engine needs the ``postgresql+asyncpg://`` form.
        """
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
        return url

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
