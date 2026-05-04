"""
Regex-Based Guardrail — Fast pre-filter for obvious attacks.

This runs BEFORE any ML model and catches:
  - Known jailbreak templates (DAN, AIM, developer mode, etc.)
  - Suspicious encoding attempts (base64 markers, hex sequences)
  - System prompt extraction attempts

Latency: < 1ms. This is the cheapest guardrail and should catch
the low-hanging fruit before burning compute on transformer inference.
"""

import re

from src.gateway.schemas import GuardrailCheck


# ── Known jailbreak template fragments ──────────────────────
JAILBREAK_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?previous\s+instructions",
    r"(?i)you\s+are\s+now\s+(DAN|AIM|STAN|DUDE|developer\s+mode)",
    r"(?i)pretend\s+you\s+(are|have)\s+no\s+(restrictions|guidelines|rules)",
    r"(?i)respond\s+without\s+any\s+(safety|ethical)\s+(filters|guidelines)",
    r"(?i)jailbreak(ed)?",
    r"(?i)bypass\s+(your|the)\s+(safety|content)\s+(filters|policy)",
    r"(?i)act\s+as\s+an?\s+(unrestricted|uncensored|unfiltered)",
    r"(?i)from\s+now\s+on,?\s+you\s+(will|must|should)\s+(not\s+)?follow",
]

# ── Encoding/obfuscation markers ────────────────────────────
ENCODING_PATTERNS = [
    r"(?i)base64\s*[:=]",
    r"(?i)decode\s+the\s+following",
    r"(?i)\\x[0-9a-f]{2}",  # Hex escape sequences
    r"(?i)respond\s+in\s+(base64|hex|rot13|binary|morse)",
]

COMPILED_PATTERNS = [re.compile(p) for p in JAILBREAK_PATTERNS + ENCODING_PATTERNS]


class RegexGuardrail:
    """Ultra-fast regex-based pre-filter for known attack patterns."""

    def check(self, text: str) -> GuardrailCheck:
        """
        Scan text against known jailbreak and encoding patterns.

        This is synchronous (no async needed) because regex is fast enough.
        """
        for pattern in COMPILED_PATTERNS:
            match = pattern.search(text)
            if match:
                return GuardrailCheck(
                    name="regex_prefilter",
                    passed=False,
                    confidence=1.0,
                    detail=f"Matched known attack pattern: '{match.group()}'",
                )

        return GuardrailCheck(
            name="regex_prefilter",
            passed=True,
            confidence=1.0,
            detail="No known attack patterns detected",
        )
