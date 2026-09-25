"""End-to-end harm check (step 5, item 3): for every TEST-split attack
Laya overturns at the chosen threshold t, sends it to qwen/qwen3.8-27b
through the sandbox in campaign mode (guardrails off - justified since
strict==effective recall lost at this t, meaning these specific
overturned rows already independently pass L3/L4/OutputGuard when
checked standalone, see laya_effective_check.py), cache off (campaign
mode never touches SemanticCache), fresh session per row, judged with
the uplift rubric (redteam/judge.py).

Requires the sandbox running with CAMPAIGN_MODE_TOKEN set and this
script's AEGIS_CAMPAIGN_TOKEN env var matching it.
"""
import argparse
import asyncio
import json
import os
import sys
import uuid

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redteam.judge import judge_response, is_compliant

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_MODEL = "qwen/qwen3.8-27b"


def load_overturned_test_attacks(threshold: float) -> list[dict]:
    scores = [json.loads(l) for l in open(
        os.path.join(_REPO_ROOT, "data", "laya_scores_test.jsonl"), encoding="utf-8")]
    return [r for r in scores if r["label"] == "attack" and r["laya_confidence"] >= threshold]


async def run_harm_check(target_url: str, campaign_token: str, rows: list[dict]) -> list[dict]:
    results = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, row in enumerate(rows, 1):
            goal = row.get("goal") or row["prompt"]
            payload = {"model": TARGET_MODEL, "messages": [{"role": "user", "content": row["prompt"]}]}
            headers = {"X-Session-ID": str(uuid.uuid4()), "X-Campaign-Mode": campaign_token}
            try:
                resp = await client.post(target_url, json=payload, headers=headers)
                resp.raise_for_status()
                content = resp.json().get("content", "")
                if "[BLOCKED]" in content:
                    outcome = "blocked_by_stack"
                    score, rationale = None, None
                else:
                    score, rationale = await judge_response(client, goal, content)
                    outcome = "bypassed" if is_compliant(score) else "refused_by_model"
                results.append({
                    "prompt": row["prompt"], "goal": goal, "wrapper_type": row.get("wrapper_type"),
                    "response": content, "outcome": outcome,
                    "judge_score": score, "judge_rationale": rationale,
                })
            except Exception as exc:
                results.append({
                    "prompt": row["prompt"], "goal": goal, "wrapper_type": row.get("wrapper_type"),
                    "response": f"[ERROR] {type(exc).__name__}: {exc}", "outcome": "errored",
                    "judge_score": None, "judge_rationale": None,
                })
            print(f"  {i}/{len(rows)}  outcome={results[-1]['outcome']}")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, required=True)
    parser.add_argument("--target", default="http://127.0.0.1:8000/v1/chat/completions")
    parser.add_argument("--campaign-token", required=True)
    args = parser.parse_args()

    rows = load_overturned_test_attacks(args.threshold)
    print(f"Overturned test-split attacks at t={args.threshold}: {len(rows)}")

    results = asyncio.run(run_harm_check(args.target, args.campaign_token, rows))

    out_path = os.path.join(_REPO_ROOT, "data", "laya_harm_check.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    from collections import Counter
    counts = Counter(r["outcome"] for r in results)
    print(f"\nOutcomes: {dict(counts)}")
    print(f"Written to {out_path}")


if __name__ == "__main__":
    main()
