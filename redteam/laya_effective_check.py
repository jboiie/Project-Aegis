"""Checks, for one split's L1/L2-blocked rows, whether the row would
ALSO be blocked by L3 (toxicity), L4 (PII), or OutputGuard if L1/L2
hadn't already short-circuited it. This is what "effective recall lost"
needs: a Laya overturn only actually costs anything if the row would
otherwise reach the user - if L3/L4/OutputGuard would catch it anyway,
overturning L1/L2 is free. Requires the aegis conda env (engine deps),
NOT laya-bench - no Laya import here.

Usage: conda run -n aegis python redteam/laya_effective_check.py --split sweep
"""
import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.guardrails.toxicity import ToxicityClassifier
from src.guardrails.pii import PIIRedactor
from src.guardrails.output import OutputGuard

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREEN_RESULTS_PATH = os.path.join(_REPO_ROOT, "data", "laya_screen_results.jsonl")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", required=True, choices=["calibration", "sweep", "test"])
    args = parser.parse_args()

    out_path = os.path.join(_REPO_ROOT, "data", f"laya_effective_{args.split}.jsonl")

    rows = [json.loads(l) for l in open(SCREEN_RESULTS_PATH, encoding="utf-8")]
    rows = [r for r in rows if r["split"] == args.split and r["blocking_layer"] in ("L1", "L2")]
    print(f"{args.split} split, L1/L2-blocked: {len(rows)} rows")

    toxicity = ToxicityClassifier()
    pii = PIIRedactor()
    output_guard = OutputGuard()
    await toxicity.load()

    results = []
    for i, row in enumerate(rows):
        tox_result = await toxicity.check(row["prompt"])
        pii_result = await pii.check(row["prompt"])
        og_passed, _ = output_guard.screen_output(row["prompt"])
        would_pass = tox_result.passed and pii_result.passed and og_passed
        results.append({
            "row_index": i,
            "prompt": row["prompt"],
            "split": row["split"],
            "label": row["label"],
            "would_pass_l3_l4_outputguard": would_pass,
        })
        if (i + 1) % 200 == 0:
            print(f"  checked {i + 1}/{len(rows)}")

    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"Written to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
