"""
Project Aegis — FastAPI Application Entry Point

This is the main application factory. It wires together:
  1. The proxy gateway (routes incoming prompts)
  2. The guardrail engine (screens prompts for safety)
  3. The semantic cache (blocks known-malicious prompts instantly)
  4. The telemetry logger (ships events to Supabase)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import settings
from src.cache.redis_client import RedisCache
from src.gateway.router import router as gateway_router
from src.telemetry.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown lifecycle hooks."""
    # ── Startup ──────────────────────────────────────────────
    setup_logging(settings.LOG_LEVEL)

    # Initialize Redis connection pool
    app.state.cache = RedisCache(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
    )
    await app.state.cache.connect()

    # TODO: Load guardrail models into memory here
    # app.state.guardrail_engine = GuardrailEngine(...)

    yield

    # ── Shutdown ─────────────────────────────────────────────
    await app.state.cache.disconnect()


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="Project Aegis",
        description="Autonomous LLM Security Proxy & Red-Teaming Pipeline",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(gateway_router, prefix="/v1")

    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
