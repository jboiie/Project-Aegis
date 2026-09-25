"""Recovers L2 (injection_detection) confidence scores for rows
currently blocked_by=L2, on sweep+test splits. Not saved by the
original laya_screen_batch.py run (only pass/fail was kept). This is
the minimal way to get this data: calls InjectionDetector().check()
directly (the local DeBERTa classifier only - no L1/L3/L4, no Groq,
no full engine.screen() re-run) on exactly the 2425 rows already known
to be blocked_by=L2, not a re-screen of the full attack/benign sets.
Raising L2's threshold can only ever un-block a currently-L2-blocked
row (a stricter threshold blocks a superset, a looser one a subset of
what 0.85 already blocks) - so no other rows need scoring for this baseline.
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.guardrails.injection import InjectionDetector

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


async def main():
    rows = [json.loads(l) for l in open(os.path.join(_REPO_ROOT, "data", "laya_screen_results.jsonl"), encoding="utf-8")]
    target = [r for r in rows if r["split"] in ("sweep", "test") and r["blocking_layer"] == "L2"]
    print(f"scoring {len(target)} L2-blocked rows (sweep+test)")

    detector = InjectionDetector()
    await detector.load()

    results = []
    for i, row in enumerate(target, 1):
        check = await detector.check(row["prompt"])
        results.append({**row, "l2_confidence": check.confidence})
        if i % 200 == 0:
            print(f"  {i}/{len(target)}")

    out_path = os.path.join(_REPO_ROOT, "data", "l2_confidence_scores.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"Written to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
