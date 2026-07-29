import asyncio
import httpx
import structlog

from src.config import settings
from src.gateway.schemas import ChatRequest

logger = structlog.get_logger()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
_MAX_RETRIES = 3
_RETRY_WAIT = 62  # seconds — Groq resets its per-minute window every 60s


async def forward_to_llm(request: ChatRequest) -> dict:
    """
    Forward a validated request to Groq and return the raw response.

    Retries up to _MAX_RETRIES times on 429 (rate limit), waiting for
    Groq's window to reset between attempts. Returns a structured error
    dict (never raises) so the sandbox always returns valid JSON.

    Args:
        request: The user's chat request (already screened by guardrails).

    Returns:
        Raw JSON response from Groq API, or structured error on failure.
    """
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": request.model or settings.GROQ_MODEL,
        "messages": [msg.model_dump() for msg in request.messages],
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(1, _MAX_RETRIES + 1):
            response = await client.post(GROQ_API_URL, json=payload, headers=headers)

            if response.status_code == 429:
                wait = _RETRY_WAIT * attempt
                logger.warning(
                    "groq_rate_limited",
                    attempt=attempt,
                    max_retries=_MAX_RETRIES,
                    wait_seconds=wait,
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(wait)
                    continue
                # Exhausted retries — return a structured error the runner can parse
                return {
                    "choices": [{"message": {"content": "[ERROR] Groq rate limit exhausted after retries"}}],
                    "model": settings.GROQ_MODEL,
                    "_aegis_error": "rate_limited",
                }

            response.raise_for_status()
            return response.json()
