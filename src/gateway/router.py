"""
Gateway Router — FastAPI routes for the proxy.

Exposes an OpenAI-compatible /v1/chat/completions endpoint so any
client library (openai-python, langchain, etc.) can point at Aegis
with zero code changes.
"""

from fastapi import APIRouter, Request
from src.gateway.schemas import ChatRequest, ChatResponse
from src.gateway.proxy import forward_to_llm
from src.guardrails.engine import GuardrailEngine

router = APIRouter(tags=["gateway"])


@router.post("/chat/completions", response_model=ChatResponse)
async def chat_completions(request: ChatRequest, raw_request: Request):
    """
    Main proxy endpoint.

    Pipeline:
      1. Check semantic cache → instant block if known-malicious
      2. Run guardrail fleet (injection, toxicity, PII)
      3. If safe → forward to target LLM (Groq)
      4. Screen LLM response (output guardrails)
      5. Log everything to telemetry
      6. Return response to user
    """
    prompt = request.messages[-1].content

    # TODO (Step 4): use app.state.guardrail_engine instead of per-request init
    engine = GuardrailEngine()
    verdict = await engine.screen(prompt)
    if not verdict.passed:
        return ChatResponse.blocked(verdict)

    # TODO: semantic cache lookup (not yet wired)
    # TODO: output guardrails (not yet wired)
    # TODO: telemetry logging (not yet wired)

    llm_response = await forward_to_llm(request)
    content = llm_response["choices"][0]["message"]["content"]

    return ChatResponse(
        content=content,
        model=request.model,
        safety=verdict,
    )
