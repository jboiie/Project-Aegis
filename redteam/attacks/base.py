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
    bypassed: bool          # True iff outcome == "bypassed" - kept for existing
                             # consumers (report.py, evaluation/metrics.py,
                             # the dashboard) that already treat
                             # "not bypassed, not errored" as blocked, which
                             # is still correct under the 4-outcome model.
    confidence: float       # How confident we are in the bypass assessment
    metadata: dict = None   # Strategy-specific metadata
    timestamp: str = ""     # ISO 8601, stamped by the runner when the result comes back
    errored: bool = False   # True if a request/API failure prevented a real verdict -
                             # a separate outcome from bypassed/blocked, excluded from ASR.
                             # bypassed is meaningless (left False) when this is True.

    # 4-outcome classification (PROJECT_DESC.md's success-judge audit):
    # "blocked_by_stack" | "refused_by_model" | "bypassed" | "errored".
    # Mutually exclusive. bypassed/errored above are derived from this but
    # kept as their own fields for existing consumers; outcome is the
    # authoritative field and what --export-jsonl rows should be read by.
    outcome: str = ""
    judge_score: int | None = None    # 1-10, PAIR-paper style (see redteam/judge.py). None if never judged (blocked_by_stack, errored).
    judge_rationale: str | None = None

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
