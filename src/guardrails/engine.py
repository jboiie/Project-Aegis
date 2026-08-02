"""
Aegis Sandbox — Guardrail Engine

This guardrail stack exists as a live attack target for the red-teaming pipeline.
It is intentionally imperfect — the pipeline's job is to find where it fails.

Each layer catches a different class of attack and is instrumented to log bypass
events so the pipeline can compute per-layer ASR (Attack Success Rate). The goal
is not to build a perfect defender — it is to build an honest, measurable one that
the pipeline can continuously probe and report against.

Defense layers in order of execution:
  SessionGuard: rejection-velocity lockout — breaks adaptive-attacker feedback loops
  L0: Semantic cache          — blocks near-duplicates of known-blocked prompts (< 5ms)
  L1: Regex pre-filter        — catches explicit jailbreak templates (< 1ms)
  L2: DeBERTa injection       — catches semantic injection attempts (~10ms)
  L3: Toxicity classifier     — catches overtly harmful content (~10ms)
  L4: PII redaction           — catches standard PII formats (~5ms)
  OutputGuard: dual-pass response screening — catches response-stage failures (see below)

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
    classifiers — caught by OutputGuard instead, see below).
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
    Caught by OutputGuard (src/guardrails/output.py), which scans responses
    for system prompt leak patterns after the LLM call, not the input.

See docs/prior_work.md for the full empirical findings that motivated this design.
"""

from src.gateway.schemas import SafetyVerdict, GuardrailCheck
from src.guardrails.regex_rules import RegexGuardrail
from src.guardrails.injection import InjectionDetector
from src.guardrails.toxicity import ToxicityClassifier
from src.guardrails.pii import PIIRedactor
from src.guardrails.session import SessionGuard
from src.guardrails.output import OutputGuard
from src.cache.redis_client import RedisCache
from src.cache.semantic import SemanticCache
from src.utils.embeddings import EmbeddingModel


class GuardrailEngine:
    """
    Orchestrates all guardrail checks against incoming prompts.

    Usage:
        engine = GuardrailEngine()
        await engine.load_models()
        verdict = await engine.screen("Tell me how to hack a bank")
    """

    def __init__(
        self,
        injection_threshold: float = 0.85,
        toxicity_threshold: float = 0.80,
        redis_cache: RedisCache | None = None,
    ):
        self.injection_threshold = injection_threshold
        self.toxicity_threshold = toxicity_threshold

        # Fast, no-ML checks run first
        self.regex = RegexGuardrail()
        self.session_guard = SessionGuard()
        self.output_guard = OutputGuard()

        # ML-based checks (loaded lazily)
        self.injection = InjectionDetector()
        self.toxicity = ToxicityClassifier()
        self.pii = PIIRedactor()

        # L0: semantic cache of known-blocked prompts (near-duplicate PAIR iterations)
        self.semantic_cache: SemanticCache | None = None
        if redis_cache is not None:
            self.semantic_cache = SemanticCache(redis=redis_cache, embedder=EmbeddingModel())

    async def load_models(self):
        """Load all ML model weights into memory. Call once at startup."""
        await self.injection.load()
        await self.toxicity.load()
        if self.semantic_cache is not None:
            self.semantic_cache.embedder.load()
        # PII uses regex + spaCy NER — no heavy model needed

    async def screen(self, text: str, session_id: str | None = None) -> SafetyVerdict:
        """
        Run all guardrails against the input text.

        Returns:
            SafetyVerdict with pass/fail and per-check details.
        """
        from src.config import settings
        enabled = set(settings.GUARDRAIL_LAYERS.split(","))

        # Check session lockout (PAIR defense)
        if session_id and self.session_guard.is_session_locked(session_id):
            lock_check = GuardrailCheck(
                name="session_guard",
                passed=False,
                confidence=1.0,
                detail="Session rate limited due to repeated safety rejections (PAIR defense active)",
            )
            return SafetyVerdict(
                passed=False,
                checks=[lock_check],
                blocked_reason=lock_check.detail,
            )

        # ── Layer 0: Semantic cache — near-duplicate of a known-blocked prompt (< 5ms) ──
        if self.semantic_cache is not None:
            is_threat, similarity = await self.semantic_cache.check(text)
            if is_threat:
                cache_check = GuardrailCheck(
                    name="semantic_cache",
                    passed=False,
                    confidence=similarity,
                    detail=f"Matched known-blocked prompt (similarity={similarity:.3f})",
                )
                if session_id:
                    self.session_guard.record_rejection(session_id)
                return SafetyVerdict(
                    passed=False,
                    checks=[cache_check],
                    blocked_reason=cache_check.detail,
                )

        checks: list[GuardrailCheck] = []

        # ── Layer 1: Regex pre-filter (< 1ms) ───────────────
        if "L1" in enabled:
            regex_result = self.regex.check(text)
            checks.append(regex_result)
            if not regex_result.passed:
                if session_id:
                    self.session_guard.record_rejection(session_id)
                if self.semantic_cache is not None:
                    await self.semantic_cache.add_malicious(text, reason=regex_result.detail)
                return SafetyVerdict(
                    passed=False,
                    checks=checks,
                    blocked_reason=regex_result.detail,
                )

        # ── Layer 2: Injection detection (DeBERTa, ~300ms) ──
        if "L2" in enabled:
            injection_result = await self.injection.check(text)
            checks.append(injection_result)
            if not injection_result.passed:
                if session_id:
                    self.session_guard.record_rejection(session_id)
                if self.semantic_cache is not None:
                    await self.semantic_cache.add_malicious(text, reason=injection_result.detail)
                return SafetyVerdict(
                    passed=False,
                    checks=checks,
                    blocked_reason=injection_result.detail,
                )

        # ── Layer 3: Toxicity classification (~150ms) ────────
        if "L3" in enabled:
            toxicity_result = await self.toxicity.check(text)
            checks.append(toxicity_result)
            if not toxicity_result.passed:
                if session_id:
                    self.session_guard.record_rejection(session_id)
                if self.semantic_cache is not None:
                    await self.semantic_cache.add_malicious(text, reason=toxicity_result.detail)
                return SafetyVerdict(
                    passed=False,
                    checks=checks,
                    blocked_reason=toxicity_result.detail,
                )

        # ── Layer 4: PII redaction (~5ms) ────────────────────
        if "L4" in enabled:
            pii_result = await self.pii.check(text)
            checks.append(pii_result)

        all_passed = all(c.passed for c in checks)
        if not all_passed and session_id:
            self.session_guard.record_rejection(session_id)

        return SafetyVerdict(
            passed=all_passed,
            checks=checks,
            blocked_reason="" if all_passed else "PII detected in prompt",
        )
