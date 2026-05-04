"""
Centralized configuration via pydantic-settings.

All values are loaded from environment variables / .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings — loaded from .env or environment."""

    # ── Target LLM ───────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # ── Redis ────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # ── Supabase ─────────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # ── Guardrail Thresholds ─────────────────────────────────
    GUARDRAIL_INJECTION_THRESHOLD: float = 0.85
    GUARDRAIL_TOXICITY_THRESHOLD: float = 0.80
    SEMANTIC_CACHE_SIMILARITY_THRESHOLD: float = 0.92

    # ── Server ───────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "info"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
