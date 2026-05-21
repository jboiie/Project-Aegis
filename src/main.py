"""
Aegis Sandbox — FastAPI Application Entry Point

NOTE: This is the SANDBOX TARGET, not the primary system.
The primary system is the red-teaming pipeline in redteam/runner.py.
This sandbox exists as a live, instrumented attack target for that pipeline.

This factory wires together the sandbox components:
  1. The gateway (OpenAI-compatible endpoint the pipeline attacks)
  2. The guardrail stack (four-layer defense the pipeline measures against)
  3. The semantic cache (blocks known-bad embeddings in < 5ms)
  4. The telemetry logger (logs every attack attempt, verdict, and bypass)
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
        title="Aegis Sandbox",
        description="Autonomous LLM red-teaming pipeline with a live guardrail sandbox as its attack target. This is the sandbox — see redteam/ for the pipeline.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(gateway_router, prefix="/v1")

    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
