"""
Groq LLM Provider — Primary target LLM backend.

Uses Groq's OpenAI-compatible API for ultra-fast inference
on Llama 3 models via their free tier.

Groq free tier limits (as of 2026):
  - 30 RPM, 14,400 RPD for llama-3.3-70b-versatile
  - Sufficient for development and red-teaming experiments
"""

import httpx

from src.config import settings
from src.gateway.schemas import ChatRequest
from src.llm.base import BaseLLMProvider


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(BaseLLMProvider):
    """Groq API client for Llama 3 inference."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL

    async def complete(self, request: ChatRequest) -> dict:
        """Forward request to Groq API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": request.model or self.model,
            "messages": [msg.model_dump() for msg in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(GROQ_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    def name(self) -> str:
        return f"groq/{self.model}"
