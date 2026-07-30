"""
Session Rejection Tracker Guardrail — Defense against iterative PAIR attacks.

Attacker LLMs (PAIR) rely on receiving rejection messages and iteratively
refining their prompts across multiple turns.

This module tracks safety rejection frequency per client session/IP.
If a client receives more than `max_rejections` blocked verdicts within
`window_seconds`, the session is temporarily locked out.

This directly neutralizes adaptive LLM red-teaming by breaking the feedback loop.
"""

import time
from collections import defaultdict
import structlog

logger = structlog.get_logger()


class SessionGuard:
    """Tracks per-session rejection velocity to block PAIR-style iterative attacks."""

    def __init__(self, max_rejections: int = 3, window_seconds: float = 300.0):
        self.max_rejections = max_rejections
        self.window_seconds = window_seconds
        # Maps session_id -> list of rejection timestamps
        self._rejections: dict[str, list[float]] = defaultdict(list)

    def is_session_locked(self, session_id: str) -> bool:
        """Check if a session is currently locked out due to high rejection velocity."""
        now = time.time()
        timestamps = self._rejections[session_id]
        # Clean up old timestamps outside the window
        valid_timestamps = [t for t in timestamps if now - t <= self.window_seconds]
        self._rejections[session_id] = valid_timestamps

        return len(valid_timestamps) >= self.max_rejections

    def record_rejection(self, session_id: str) -> None:
        """Record a safety rejection for a session."""
        now = time.time()
        self._rejections[session_id].append(now)
        logger.warning(
            "session_rejection_recorded",
            session_id=session_id,
            rejection_count=len(self._rejections[session_id]),
            max_allowed=self.max_rejections,
        )

    def reset_session(self, session_id: str) -> None:
        """Clear rejection history for a session."""
        if session_id in self._rejections:
            del self._rejections[session_id]
