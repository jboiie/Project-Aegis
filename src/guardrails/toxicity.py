"""
Toxicity Classification — Detects harmful / unsafe content.

Uses a pre-trained toxicity model (e.g., unitary/toxic-bert or
a fine-tuned DeBERTa variant) to flag harmful content before
it reaches the target LLM.
"""

from src.gateway.schemas import GuardrailCheck


class ToxicityClassifier:
    """Classifies text for toxicity, hate speech, and harmful content."""

    def __init__(self, model_name: str = "unitary/toxic-bert", threshold: float = 0.80):
        self.model_name = model_name
        self.threshold = threshold
        self.pipeline = None

    async def load(self):
        """Load the toxicity model. Call once at startup."""
        # TODO: Uncomment when ready
        # from transformers import pipeline
        # self.pipeline = pipeline(
        #     "text-classification",
        #     model=self.model_name,
        #     device=-1,
        # )
        pass

    async def check(self, text: str) -> GuardrailCheck:
        """Screen text for toxic content."""
        if self.pipeline is None:
            return GuardrailCheck(
                name="toxicity_check",
                passed=True,
                confidence=0.0,
                detail="Model not loaded — skipping toxicity check",
            )

        result = self.pipeline(text[:512])[0]
        is_toxic = result["label"] == "toxic"
        confidence = result["score"]

        if is_toxic and confidence >= self.threshold:
            return GuardrailCheck(
                name="toxicity_check",
                passed=False,
                confidence=confidence,
                detail=f"Toxic content detected (confidence: {confidence:.3f})",
            )

        return GuardrailCheck(
            name="toxicity_check",
            passed=True,
            confidence=confidence,
            detail="Content is safe",
        )
