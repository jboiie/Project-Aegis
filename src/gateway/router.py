"""
Gateway Router — FastAPI routes for the proxy.

Exposes an OpenAI-compatible /v1/chat/completions endpoint so any
client library (openai-python, langchain, etc.) can point at Aegis
with zero code changes.
"""

from fastapi import APIRouter, Request
from src.gateway.schemas import ChatRequest, ChatResponse
from src.gateway.proxy import forward_to_llm

router = APIRouter(tags=["gateway"])


@router.post("/chat/completions", response_model=ChatResponse)
async def chat_completions(request: ChatRequest, raw_request: Request):
    """
    Main proxy endpoint.

    Pipeline:
      1. Extract session identifier (X-Session-ID header or client IP)
      2. Check session lockout velocity (PAIR defense)
      3. Run guardrail fleet (L1 Regex, L2 DeBERTa, L3 Toxicity, L4 PII)
      4. Forward safe requests to target LLM (Groq)
      5. Dual-pass output screening on generated response
      6. Return response to user
    """
    prompt = request.messages[-1].content
    session_id = raw_request.headers.get("X-Session-ID") or (
        raw_request.client.host if raw_request.client else "default_session"
    )

    engine = raw_request.app.state.guardrail_engine
    verdict = await engine.screen(prompt, session_id=session_id)
    if not verdict.passed:
        return ChatResponse.blocked(verdict)

    llm_response = await forward_to_llm(request)
    raw_content = llm_response["choices"][0]["message"]["content"]

    # Dual-pass output screening
    output_passed, final_content = engine.output_guard.screen_output(raw_content)
    if not output_passed:
        verdict.passed = False
        verdict.blocked_reason = final_content

    return ChatResponse(
        content=final_content,
        model=request.model,
        safety=verdict,
    )

