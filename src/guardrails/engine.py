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
saving inference cycles for the harder cases that reach L2/L3.

Empirical basis for this layer design (from prior pair-lab and prompt-autopsy runs):

  WHAT BYPASSES OPEN-WEIGHT MODELS (and therefore needs to be caught here):
  - Role-play & authority framing: academic/researcher persona + sensitive topic.
    L1 regex catches known templates (DAN). L2 must score the *combination*
    of authority claim + sensitive topic, not keywords in isolation.
  - "Educational purposes" framing: shifts model into teacher mode.
    L3 toxicity classifier must catch the harmful content of the *response*
    even when the *input* framing appears benign (out-of-scope for input-only
    classifiers — see TODO for output scanner).
  - Inline token injection: `###SYSTEM`, `[INST]` injected into user prompt.
    L1 regex handles this via structural token pattern matching.
  - Obfuscation (Base64, leetspeak): encoded payloads cause unpredictable
    behavior — model may comply, hallucinate, or refuse. L2/L3 classifiers
    trained on plaintext do not generalize to encoded inputs reliably.

  KNOWN GAPS (what this stack does NOT catch — by design, for measurement):
  - Authority framing with novel personas not in the L1 regex corpus
  - Harmful content wrapped in multi-step fictional narratives (L3 miss)
  - Prompt exfiltration: asking the model to repeat its system prompt.
    This is a *response-layer* failure, not an input-layer failure.
    TODO: output scanner — scan responses for system prompt leak patterns
    and functional code execution when input was flagged medium/high risk.

See docs/prior_work.md for the full empirical findings that motivated this design.
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
