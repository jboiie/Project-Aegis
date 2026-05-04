"""
PII Redaction — Detects and masks personally identifiable information.

Uses regex patterns for common PII types (emails, phone numbers,
credit cards, SSNs) and optionally spaCy NER for names/addresses.

Design note: This is a "defense-in-depth" layer. Even if the LLM
itself doesn't leak PII, we catch it in the prompt before it's
ever sent to a third-party API.
"""

import re

from src.gateway.schemas import GuardrailCheck


# ── Regex patterns for common PII ────────────────────────────
PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "aadhaar": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),  # Indian Aadhaar
}


class PIIRedactor:
    """Detects PII in text and optionally redacts it."""

    async def check(self, text: str) -> GuardrailCheck:
        """
        Scan text for PII patterns.

        Returns:
            GuardrailCheck — passes if no PII found, fails otherwise.
        """
        found_types: list[str] = []

        for pii_type, pattern in PII_PATTERNS.items():
            if pattern.search(text):
                found_types.append(pii_type)

        if found_types:
            return GuardrailCheck(
                name="pii_detection",
                passed=False,
                confidence=1.0,
                detail=f"PII detected: {', '.join(found_types)}",
            )

        return GuardrailCheck(
            name="pii_detection",
            passed=True,
            confidence=1.0,
            detail="No PII detected",
        )

    def redact(self, text: str) -> str:
        """Replace PII in text with [REDACTED] placeholders."""
        redacted = text
        for pii_type, pattern in PII_PATTERNS.items():
            redacted = pattern.sub(f"[{pii_type.upper()}_REDACTED]", redacted)
        return redacted
