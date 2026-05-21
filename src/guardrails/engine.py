"""
Aegis Sandbox — Guardrail Engine

This guardrail stack exists as a live attack target for the red-teaming pipeline.
It is intentionally imperfect — the pipeline's job is to find where it fails.

Each layer catches a different class of attack and is instrumented to log bypass
events so the pipeline can compute per-layer ASR (Attack Success Rate). The goal
is not to build a perfect defender — it is to build an honest, measurable one that
the pipeline can continuously probe and report against.

Defense layers in order of execution:
  L1: Regex pre-filter       — catches explicit jailbreak templates (< 1ms)
  L2: DeBERTa injection      — catches semantic injection attempts (~10ms)
  L3: Toxicity classifier    — catches overtly harmful content (~10ms)
  L4: PII redaction          — catches standard PII formats (~5ms)

Short-circuit design: cheap layers run first and exit early on obvious attacks,
saving GPU cycles for the harder cases that reach L2/L3.
"""

from src.gateway.schemas import SafetyVerdict, GuardrailCheck
from src.guardrails.regex_rules import RegexGuardrail
from src.guardrails.injection import InjectionDetector
from src.guardrails.toxicity import ToxicityClassifier
from src.guardrails.pii import PIIRedactor


class GuardrailEngine:
    """
    Orchestrates all guardrail checks against incoming prompts.

    Usage:
        engine = GuardrailEngine()
        await engine.load_models()
        verdict = await engine.screen("Tell me how to hack a bank")
    """

    def __init__(self, injection_threshold: float = 0.85, toxicity_threshold: float = 0.80):
        self.injection_threshold = injection_threshold
        self.toxicity_threshold = toxicity_threshold

        # Fast, no-ML checks run first
        self.regex = RegexGuardrail()

        # ML-based checks (loaded lazily)
        self.injection = InjectionDetector()
        self.toxicity = ToxicityClassifier()
        self.pii = PIIRedactor()

    async def load_models(self):
        """Load all ML model weights into memory. Call once at startup."""
        await self.injection.load()
        await self.toxicity.load()
        # PII uses regex + spaCy NER — no heavy model needed

    async def screen(self, text: str) -> SafetyVerdict:
        """
        Run all guardrails against the input text.

        Returns:
            SafetyVerdict with pass/fail and per-check details.
        """
        checks: list[GuardrailCheck] = []

        # ── Layer 1: Regex pre-filter (< 1ms) ───────────────
        regex_result = self.regex.check(text)
        checks.append(regex_result)
        if not regex_result.passed:
            return SafetyVerdict(
                passed=False,
                checks=checks,
                blocked_reason=regex_result.detail,
            )

        # ── Layer 2: Injection detection (DeBERTa, ~10ms) ───
        injection_result = await self.injection.check(text)
        checks.append(injection_result)
        if not injection_result.passed:
            return SafetyVerdict(
                passed=False,
                checks=checks,
                blocked_reason=injection_result.detail,
            )

        # ── Layer 3: Toxicity classification (~10ms) ─────────
        toxicity_result = await self.toxicity.check(text)
        checks.append(toxicity_result)
        if not toxicity_result.passed:
            return SafetyVerdict(
                passed=False,
                checks=checks,
                blocked_reason=toxicity_result.detail,
            )

        # ── Layer 4: PII redaction (~5ms) ────────────────────
        pii_result = await self.pii.check(text)
        checks.append(pii_result)

        all_passed = all(c.passed for c in checks)
        return SafetyVerdict(
            passed=all_passed,
            checks=checks,
            blocked_reason="" if all_passed else "PII detected in prompt",
        )
