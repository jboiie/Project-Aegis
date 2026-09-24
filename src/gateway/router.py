"""
Gateway Router — FastAPI routes for the proxy.

Exposes an OpenAI-compatible /v1/chat/completions endpoint so any
client library (openai-python, langchain, etc.) can point at Aegis
with zero code changes.
"""

import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from src.config import settings
from src.gateway.schemas import ChatRequest, ChatResponse, GuardrailCheck, SafetyVerdict
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
      6. Log the event to telemetry
      7. Return response to user
    """
    prompt = request.messages[-1].content
    session_id = raw_request.headers.get("X-Session-ID") or (
        raw_request.client.host if raw_request.client else "default_session"
    )
    start_time = time.perf_counter()
    telemetry = raw_request.app.state.telemetry

    engine = raw_request.app.state.guardrail_engine

    # Campaign-mode bypass: only active if CAMPAIGN_MODE_TOKEN is set AND
    # the request carries a matching header - normal requests (the common
    # case, and the startup probe's own direct regex.check() call) are
    # completely unaffected. See src/config.py's CAMPAIGN_MODE_TOKEN
    # comment and PROJECT_DESC.md's guardrails-off-ablation design.
    skip_guardrails = (
        bool(settings.CAMPAIGN_MODE_TOKEN)
        and raw_request.headers.get("X-Campaign-Mode") == settings.CAMPAIGN_MODE_TOKEN
    )
    if skip_guardrails:
        verdict = SafetyVerdict(passed=True, checks=[], blocked_reason="")
    else:
        verdict = await engine.screen(prompt, session_id=session_id)
    if not verdict.passed:
        await telemetry.log_event(
            prompt=prompt,
            blocked=True,
            blocked_reason=verdict.blocked_reason,
            checks=[c.model_dump() for c in verdict.checks],
            latency_ms=(time.perf_counter() - start_time) * 1000,
            model=request.model,
        )
        return ChatResponse.blocked(verdict)

    try:
        llm_response = await forward_to_llm(request)
        raw_content = llm_response["choices"][0]["message"]["content"]
    except Exception as exc:
        # A request/API failure (dead model, timeout, target 500) is a
        # separate outcome from blocked/allowed - previously this had no
        # try/except at all here, so the exception crashed past this point
        # unhandled: a raw 500 to the client, and telemetry.log_event()
        # below never ran, meaning the failure left NO row in aegis_events,
        # not even a misleading one. See PROJECT_DESC.md's error-handling
        # audit, found via the aegis_events check for the llama-3.3-70b
        # retirement's effect on historical campaigns.
        #
        # 502, not 200: template.py/encoding.py detect a request failure
        # via response.raise_for_status(), which only fires on a non-2xx
        # status. A 200 response with "[ERROR]" text in the body content
        # would silently pass raise_for_status(), get parsed as a normal
        # (refused) completion, and get counted as blocked - the same class
        # of bug just fixed in pair.py, one layer up in the stack.
        detail = f"{type(exc).__name__}: {exc}"
        await telemetry.log_event(
            prompt=prompt,
            blocked=False,
            blocked_reason=f"[ERROR] {detail}",
            checks=[c.model_dump() for c in verdict.checks],
            latency_ms=(time.perf_counter() - start_time) * 1000,
            model=request.model,
            errored=True,
        )
        return JSONResponse(
            status_code=502,
            content={"error": {"message": detail, "type": "target_llm_error"}},
        )

    # Dual-pass output screening
    output_passed, final_content = engine.output_guard.screen_output(raw_content)
    if not output_passed:
        verdict.passed = False
        verdict.blocked_reason = final_content

    await telemetry.log_event(
        prompt=prompt,
        blocked=not verdict.passed,
        blocked_reason=verdict.blocked_reason,
        checks=[c.model_dump() for c in verdict.checks],
        latency_ms=(time.perf_counter() - start_time) * 1000,
        model=request.model,
    )

    return ChatResponse(
        content=final_content,
        model=request.model,
        safety=verdict,
    )

