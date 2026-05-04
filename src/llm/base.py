"""
Base LLM Provider — Abstract interface for target LLM backends.

All LLM providers (Groq, OpenRouter, local) implement this interface
so the proxy is backend-agnostic.
"""

from abc import ABC, abstractmethod
from src.gateway.schemas import ChatRequest


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def complete(self, request: ChatRequest) -> dict:
        """
        Send a chat completion request to the target LLM.

        Args:
            request: The validated, guardrail-screened chat request.

        Returns:
            Raw response dict from the LLM API.
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """Provider name for logging."""
        ...
