"""
Base Attack — Abstract interface for all attack strategies.

Every attack strategy must:
  1. Generate a malicious prompt
  2. Send it to the target proxy
  3. Determine if the attack bypassed the guardrails
  4. Return a structured AttackResult
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AttackResult:
    """Result of a single attack attempt."""
    strategy: str           # e.g. "pair", "encoding", "template"
    prompt: str             # The attack prompt that was sent
    response: str           # The proxy's response
    bypassed: bool          # True if the attack got through
    confidence: float       # How confident we are in the bypass assessment
    metadata: dict = None   # Strategy-specific metadata

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseAttack(ABC):
    """Abstract base class for attack strategies."""

    @abstractmethod
    async def execute(self, target_url: str) -> AttackResult:
        """
        Execute a single attack attempt.

        Args:
            target_url: The Aegis proxy endpoint to attack.

        Returns:
            AttackResult with bypass assessment.
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """Strategy name for logging."""
        ...
