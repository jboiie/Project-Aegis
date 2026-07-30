"""
Output Guardrail — Dual-Pass Verification on LLM Responses.

Even if an obfuscated attack prompt slips past L1-L4 input classifiers,
the output guardrail screens the target LLM's generated response before
returning it to the client.

Checks:
  1. Refusal Failure Check: Ensures the model didn't execute harmful instructions (e.g. step-by-step hacking guides).
  2. Harmful Content Patterns: Detects explicit malicious instructions or dangerous code snippets.
"""

import re
import structlog

logger = structlog.get_logger()

# Key indicators of unhandled harmful outputs
HARMFUL_OUTPUT_PATTERNS = [
    r"step \d+: .*hack",
    r"here is how to (create|build|make) a (virus|malware|weapon|bomb)",
    r"eval\(base64_decode",
    r"system\(['\"].*rm -rf",
]


class OutputGuard:
    """Screen generated LLM responses prior to client delivery."""

    def __init__(self):
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in HARMFUL_OUTPUT_PATTERNS]

    def screen_output(self, response_text: str) -> tuple[bool, str]:
        """
        Screen the output response.

        Returns:
            (passed: bool, output_or_redacted: str)
        """
        for pattern in self._compiled_patterns:
            if pattern.search(response_text):
                logger.warning("output_guardrail_triggered", pattern=pattern.pattern)
                return False, "[BLOCKED] Response redacted by Aegis Output Guardrail (harmful output detected)."

        return True, response_text
