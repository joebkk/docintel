"""Configuration management for agent system."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # RAG Backend
    rag_api_url: str = Field(default="http://localhost:3000")
    rag_api_key: str | None = None

    # Google Gemini
    google_api_key: str
    gemini_model: str = "gemini-2.0-flash-exp"

    # MongoDB
    mongodb_uri: str
    mongodb_database: str = "docurepo"
    memory_bank_collection: str = "agent_memory"

    # OpenAI
    openai_api_key: str

    # Observability
    log_level: str = "INFO"
    enable_tracing: bool = True
    enable_metrics: bool = True
    prometheus_port: int = 9090

    # Agent Configuration
    max_iterations: int = 3
    quality_threshold: float = 0.85
    context_max_length: int = 100000

    # Session Storage
    session_storage_path: str = "./sessions"

    # Google Search (optional)
    google_search_api_key: str | None = None
    google_search_engine_id: str | None = None


# Global settings instance
settings = Settings()
