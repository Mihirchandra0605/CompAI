"""Application configuration using Pydantic Settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings — loaded from environment variables."""

    # Application
    app_name: str = "CompliAI"
    app_version: str = "0.1.0"
    debug: bool = True
    log_level: str = "INFO"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    # LLM
    openai_api_key: str = ""
    llm_model: str = "gpt-4"
    llm_temperature: float = 0.0

    # Persistence
    database_url: str = "sqlite+aiosqlite:///./data/compliai.db"

    # Observability
    langsmith_api_key: str = ""
    langsmith_project: str = "compliai-v1"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
