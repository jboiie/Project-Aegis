"""
Aegis Sandbox — Proxy Layer

NOTE: This is a sandbox component, not the primary system.
The primary system is the red-teaming pipeline in redteam/runner.py.

This module forwards prompts that survive the guardrail stack to Groq's LLM.
It is the final stage of the sandbox pipeline, reached only when L1–L4 defenses
do not block the incoming prompt. The red-teaming pipeline measures how often
attacks reach this stage by inspecting the sandbox's response.
"""

import httpx

from src.config import settings
from src.gateway.schemas import ChatRequest


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


async def forward_to_llm(request: ChatRequest) -> dict:
    """
    Forward a validated request to Groq and return the raw response.

    Args:
        request: The user's chat request (already screened by guardrails).

    Returns:
        Raw JSON response from Groq API.
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
        response = await client.post(GROQ_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
