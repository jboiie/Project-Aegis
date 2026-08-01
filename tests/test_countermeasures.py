"""Unit tests for SessionGuard and OutputGuard defenses."""

import pytest
from src.guardrails.session import SessionGuard
from src.guardrails.output import OutputGuard
from src.guardrails.engine import GuardrailEngine


def test_session_guard_lockout():
    """Verify that SessionGuard locks out a session after max_rejections."""
    guard = SessionGuard(max_rejections=3, window_seconds=60)
    session_id = "test_session_123"

    assert not guard.is_session_locked(session_id)

    # Record 2 rejections — should still be unlocked
    guard.record_rejection(session_id)
    guard.record_rejection(session_id)
    assert not guard.is_session_locked(session_id)

    # Record 3rd rejection — should now be locked
    guard.record_rejection(session_id)
    assert guard.is_session_locked(session_id)

    # Reset session — should unlock
    guard.reset_session(session_id)
    assert not guard.is_session_locked(session_id)


def test_output_guard_detection():
    """Verify that OutputGuard detects harmful response patterns and redacts content."""
    guard = OutputGuard()

    # Safe response
    passed, content = guard.screen_output("Here is the answer to your question about math.")
    assert passed
    assert "math" in content

    # Malicious output attempt
    passed_bad, content_bad = guard.screen_output("Step 1: Hack into the network using a backdoor script")
    assert not passed_bad
    assert "[BLOCKED]" in content_bad


async def test_engine_returns_verdict_on_session_lockout():
    """
    Regression test: GuardrailEngine.screen() must not crash when a session
    is locked out. Previously the lockout path built a GuardrailCheck with
    fields that don't exist on the schema (layer/score/threshold instead of
    name/confidence), which raised a pydantic ValidationError -> 500 on every
    locked request instead of returning a clean blocked verdict.
    """
    engine = GuardrailEngine()  # no redis_cache -> semantic cache disabled, no ML models loaded
    session_id = "locked_session"

    engine.session_guard.record_rejection(session_id)
    engine.session_guard.record_rejection(session_id)
    engine.session_guard.record_rejection(session_id)
    assert engine.session_guard.is_session_locked(session_id)

    verdict = await engine.screen("anything", session_id=session_id)

    assert not verdict.passed
    assert verdict.checks[0].name == "session_guard"
    assert "rate limited" in verdict.blocked_reason.lower()
