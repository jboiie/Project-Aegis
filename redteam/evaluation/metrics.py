"""
Evaluation Metrics — Quantitative assessment of guardrail effectiveness.

Computes standard ML security metrics:
  - Attack Success Rate (ASR): % of attacks that bypassed guardrails
  - Precision: Of prompts flagged as attacks, how many actually were?
  - Recall: Of actual attacks, how many did the guardrails catch?
  - F1 Score: Harmonic mean of precision and recall
  - Latency overhead: Additional ms added by the guardrail pipeline

These metrics form the evaluation table in the README.

NOTE: Precision, Recall, and F1 require a labeled benchmark dataset —
a set of prompts with known ground-truth labels (attack vs. benign).
Without this, only ASR (from the red-team run itself) can be computed.

TODO: Load labeled dataset here for Precision/Recall/F1 computation.
      Recommended: 20–30 prompt subset of JailbreakBench (JBB-Behaviors)
      as the attack set, paired with an equal-sized benign prompt set.
      Dataset path: data/labeled_eval_set.jsonl (create this file)
      Format: [{"prompt": "...", "label": "attack" | "benign"}, ...]
"""

from dataclasses import dataclass

from redteam.attacks.base import AttackResult


@dataclass
class EvaluationMetrics:
    """Aggregated evaluation metrics."""
    total: int
    true_positives: int   # Correctly blocked attacks
    false_positives: int  # Safe prompts incorrectly blocked
    true_negatives: int   # Safe prompts correctly allowed
    false_negatives: int  # Attacks that bypassed (missed)

    @property
    def attack_success_rate(self) -> float:
        """ASR — lower is better for the defender."""
        attacks = self.true_positives + self.false_negatives
        return self.false_negatives / attacks if attacks > 0 else 0.0

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    def summary(self) -> dict:
        return {
            "total_evaluated": self.total,
            "attack_success_rate": f"{self.attack_success_rate:.2%}",
            "precision": f"{self.precision:.4f}",
            "recall": f"{self.recall:.4f}",
            "f1_score": f"{self.f1:.4f}",
        }


def compute_metrics(results: list[AttackResult]) -> EvaluationMetrics:
    """
    Compute evaluation metrics from a list of attack results.

    Assumes all prompts in `results` are actual attacks (red-team
    generated), so:
      - Blocked = True Positive
      - Bypassed = False Negative
    """
    tp = sum(1 for r in results if not r.bypassed)
    fn = sum(1 for r in results if r.bypassed)

    return EvaluationMetrics(
        total=len(results),
        true_positives=tp,
        false_positives=0,   # Need benign test set for this
        true_negatives=0,    # Need benign test set for this
        false_negatives=fn,
    )
