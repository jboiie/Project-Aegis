"""
Labeled Evaluation Runner — real precision/recall/F1 against ground truth.

Unlike redteam/runner.py (which only computes ASR because every prompt it
fires is assumed to be an attack), this fires a labeled dataset — a mix of
attack and benign prompts with known ground truth — and computes real
precision, recall, and F1 from the confusion matrix.

Each request gets its own X-Session-ID (a fresh UUID) so SessionGuard's
rejection-velocity lockout — which blocks a session regardless of prompt
content, by design — can't contaminate the result. Precision/recall are
meant to measure per-prompt classification quality (L0-L4); session-level
defense is already measured separately in Phase D (see docs/technical_report.md).
Without this, one locked session blocks every subsequent prompt including
benign ones, and precision collapses to a session-lockout artifact instead
of a real number.

Usage:
    python -m redteam.evaluation.run_eval \\
        --target http://localhost:8000/v1/chat/completions \\
        --dataset data/labeled_eval_set.jsonl
"""

import asyncio
import argparse
import json
import uuid
from pathlib import Path

import httpx
import structlog

from redteam.evaluation.metrics import compute_labeled_metrics

logger = structlog.get_logger()

DEFAULT_DATASET = Path(__file__).resolve().parent.parent.parent / "data" / "labeled_eval_set.jsonl"


def load_dataset(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


async def run_eval(target_url: str, dataset_path: Path, delay: float = 2.0) -> None:
    rows = load_dataset(dataset_path)
    logger.info("eval_start", target=target_url, total=len(rows))

    labeled_results: list[tuple[str, bool]] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, row in enumerate(rows, 1):
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": row["prompt"]}],
            }
            headers = {"X-Session-ID": str(uuid.uuid4())}
            try:
                resp = await client.post(target_url, json=payload, headers=headers)
                content = resp.json().get("content", "")
                blocked = "[BLOCKED]" in content
            except Exception as e:
                logger.error("eval_request_failed", index=i, label=row["label"], error=str(e))
                blocked = False  # unreachable target -> conservative (not blocked)

            labeled_results.append((row["label"], blocked))
            logger.info("eval_result", index=i, total=len(rows), label=row["label"], blocked=blocked)
            await asyncio.sleep(delay)

    metrics = compute_labeled_metrics(labeled_results)

    print("\n" + "=" * 50)
    print("LABELED EVALUATION REPORT")
    print("=" * 50)
    print(f"  dataset:             {dataset_path}")
    print(f"  total_evaluated:     {metrics.total}")
    print(f"  true_positives:      {metrics.true_positives}  (attacks correctly blocked)")
    print(f"  false_negatives:     {metrics.false_negatives}  (attacks that bypassed)")
    print(f"  true_negatives:      {metrics.true_negatives}  (benign correctly allowed)")
    print(f"  false_positives:     {metrics.false_positives}  (benign incorrectly blocked)")
    print(f"  attack_success_rate: {metrics.attack_success_rate:.2%}")
    print(f"  precision:           {metrics.precision:.4f}")
    print(f"  recall:              {metrics.recall:.4f}")
    print(f"  f1_score:            {metrics.f1:.4f}")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aegis Labeled Evaluation — precision/recall/F1")
    parser.add_argument("--target", default="http://localhost:8000/v1/chat/completions")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--delay", type=float, default=2.0,
                         help="Seconds between requests to avoid rate limits (default: 2.0)")
    args = parser.parse_args()

    asyncio.run(run_eval(args.target, Path(args.dataset), delay=args.delay))
