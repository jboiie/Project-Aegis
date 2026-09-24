"""Tests for redteam/runner.py's run_attacks() outcome counting - no network,
uses a fake attack strategy that returns canned AttackResults."""

import pytest

from redteam.attacks.base import AttackResult, BaseAttack
from redteam.runner import ATTACK_REGISTRY, run_attacks


class _ScriptedAttack(BaseAttack):
    """Returns each AttackResult in `SCRIPT` in order, once per instance."""
    SCRIPT: list[AttackResult] = []

    def __init__(self):
        self._i = 0

    async def execute(self, target_url: str) -> AttackResult:
        result = self.SCRIPT[self._i]
        self._i += 1
        return result

    def name(self) -> str:
        return "scripted"


@pytest.fixture
def scripted_registry(monkeypatch):
    """Registers _ScriptedAttack under the name "scripted" for the duration
    of a test, restoring the real registry afterwards."""
    def _register(script: list[AttackResult]):
        cls = type("_Scripted", (_ScriptedAttack,), {"SCRIPT": script})
        monkeypatch.setitem(ATTACK_REGISTRY, "scripted", cls)
        return cls
    return _register


@pytest.mark.asyncio
async def test_errored_excluded_from_total_attacks_and_asr(scripted_registry):
    # 1 real bypass, 1 real block, 2 errored - previously pair.py's own
    # internal "[ERROR]" marker matched the same is_blocked check as a real
    # block, so an errored attempt could reach here with bypassed=False and
    # get silently counted as `blocked`. See PROJECT_DESC.md's
    # error-handling audit.
    scripted_registry([
        AttackResult(strategy="scripted", prompt="a", response="ok", bypassed=True, confidence=1.0),
        AttackResult(strategy="scripted", prompt="b", response="[BLOCKED]", bypassed=False, confidence=1.0),
        AttackResult(strategy="scripted", prompt="c", response="[ERROR] ConnectError", bypassed=False,
                     confidence=0.0, errored=True),
        AttackResult(strategy="scripted", prompt="d", response="[ERROR] ConnectError", bypassed=False,
                     confidence=0.0, errored=True),
    ])

    report = await run_attacks("http://unused", ["scripted"], num_attempts=4, delay=0.0)

    assert report.errors == 2
    assert report.total_attacks == 2          # errored rows excluded
    assert report.successful_bypasses == 1
    assert report.blocked == 1
    assert report.attack_success_rate == 0.5  # would read 0.25 if errors counted as blocked
    assert len(report.results) == 4           # all 4 still kept for --export-jsonl


@pytest.mark.asyncio
async def test_all_errored_gives_zero_total_not_zero_asr(scripted_registry):
    # An all-error run (e.g. target completely unreachable) must not read
    # as a clean 0% ASR "pass" - total_attacks should be 0, not silently
    # full of misclassified blocks.
    scripted_registry([
        AttackResult(strategy="scripted", prompt="a", response="[ERROR] ConnectError", bypassed=False,
                     confidence=0.0, errored=True),
        AttackResult(strategy="scripted", prompt="b", response="[ERROR] ConnectError", bypassed=False,
                     confidence=0.0, errored=True),
    ])

    report = await run_attacks("http://unused", ["scripted"], num_attempts=2, delay=0.0)

    assert report.errors == 2
    assert report.total_attacks == 0
    assert report.attack_success_rate == 0.0  # empty-denominator default, not a real "safe" verdict
