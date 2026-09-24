"""
Request/Response schemas — Pydantic models for the API.

Designed to be OpenAI-compatible so any client library works
out of the box by just changing the base URL.
"""

from pydantic import BaseModel, Field

from src.config import settings


class Message(BaseModel):
    """A single chat message."""
    role: str   # "system" | "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    """Incoming chat completion request (OpenAI-compatible)."""
    # default_factory, not a literal - llama-3.3-70b-versatile (the old
    # default) is retired from Groq's catalog. See PROJECT_DESC.md's
    # model-config audit.
    model: str = Field(default_factory=lambda: settings.GROQ_MODEL)
    messages: list[Message]
    temperature: float = 0.7
    max_tokens: int = 1024


class GuardrailCheck(BaseModel):
    """Result of a single guardrail check."""
    name: str               # e.g. "injection_detection"
    passed: bool
    confidence: float       # 0.0 → 1.0
    detail: str = ""        # Human-readable explanation


class SafetyVerdict(BaseModel):
    """Aggregated result of all guardrail checks."""
    passed: bool
    checks: list[GuardrailCheck]
    blocked_reason: str = ""


class ChatResponse(BaseModel):
    """Response returned to the client."""
    content: str
    model: str
    safety: SafetyVerdict

    @classmethod
    def blocked(cls, verdict: SafetyVerdict) -> "ChatResponse":
        """Factory for blocked responses."""
        return cls(
            content=f"[BLOCKED] {verdict.blocked_reason}",
            model="aegis-guardrail",
            safety=verdict,
        )
