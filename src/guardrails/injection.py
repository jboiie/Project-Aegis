"""
Prompt Injection Detection — DeBERTa-based classifier.

Uses a fine-tuned DeBERTa model to detect prompt injection attempts.
The model is fine-tuned on Colab using datasets like:
  - deepset/prompt-injections
  - JailbreakBench/JBB-Behaviors

At inference time, runs on CPU with negligible latency (~10ms).
"""

from src.gateway.schemas import GuardrailCheck


class InjectionDetector:
    """
    Detects prompt injection attacks using a fine-tuned transformer.

    The model classifies text as:
      0 → SAFE (normal user prompt)
      1 → INJECTION (attempted jailbreak / prompt injection)
    """

    def __init__(self, model_path: str = "models/injection-deberta", threshold: float = 0.85):
        self.model_path = model_path
        self.threshold = threshold
        self.pipeline = None  # Loaded lazily

    async def load(self):
        """Load the fine-tuned model. Call once at startup."""
        # TODO: Uncomment when model is trained and downloaded from Colab
        # from transformers import pipeline
        # self.pipeline = pipeline(
        #     "text-classification",
        #     model=self.model_path,
        #     device=-1,  # CPU
        # )
        pass

    async def check(self, text: str) -> GuardrailCheck:
        """
        Classify a prompt as safe or injection attempt.

        Args:
            text: The raw user prompt.

        Returns:
            GuardrailCheck with pass/fail and confidence score.
        """
        if self.pipeline is None:
            # Model not loaded — pass through (development mode)
            return GuardrailCheck(
                name="injection_detection",
                passed=True,
                confidence=0.0,
                detail="Model not loaded — skipping injection check",
            )

        result = self.pipeline(text[:512])[0]  # Truncate to model max length
        is_injection = result["label"] == "INJECTION"
        confidence = result["score"]

        if is_injection and confidence >= self.threshold:
            return GuardrailCheck(
                name="injection_detection",
                passed=False,
                confidence=confidence,
                detail=f"Prompt injection detected (confidence: {confidence:.3f})",
            )

        return GuardrailCheck(
            name="injection_detection",
            passed=True,
            confidence=1 - confidence if is_injection else confidence,
            detail="No injection detected",
        )
