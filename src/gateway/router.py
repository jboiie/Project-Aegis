"""
Gateway Router — FastAPI routes for the proxy.

Exposes an OpenAI-compatible /v1/chat/completions endpoint so any
client library (openai-python, langchain, etc.) can point at Aegis
with zero code changes.
"""

from fastapi import APIRouter, Request
from src.gateway.schemas import ChatRequest, ChatResponse, SafetyVerdict
from src.gateway.proxy import forward_to_llm

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
    # TODO: Step 1 — Semantic cache lookup
    # cache = raw_request.app.state.cache
    # cached_verdict = await cache.check_similarity(request.messages[-1].content)
    # if cached_verdict and cached_verdict.blocked:
    #     return ChatResponse.blocked(cached_verdict)

    # TODO: Step 2 — Input guardrails
    # verdict = await guardrail_engine.screen(request.messages[-1].content)
    # if verdict.blocked:
    #     await telemetry.log_blocked(request, verdict)
    #     return ChatResponse.blocked(verdict)

    # TODO: Step 3 — Forward to target LLM
    # llm_response = await forward_to_llm(request)

    # TODO: Step 4 — Output guardrails
    # output_verdict = await guardrail_engine.screen_output(llm_response)

    # TODO: Step 5 — Telemetry
    # await telemetry.log_request(request, llm_response, verdict)

    # Placeholder response until pipeline is wired
    return ChatResponse(
        content="[Aegis] Pipeline not yet wired. See TODOs in gateway/router.py",
        model=request.model,
        safety=SafetyVerdict(passed=True, checks=[]),
    )
