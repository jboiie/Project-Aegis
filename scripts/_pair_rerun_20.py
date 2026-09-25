"""PAIR-only rerun after the think-tag fix: guardrails off (campaign mode),
cache off, target qwen/qwen3.8-27b, 20 AdvBench behaviors (first 20 of the
existing seed=42 sample), 5 iterations/attempt. One attempt per behavior,
in order (not random.choice), so all 20 behaviors get tried exactly once.
"""
import asyncio
import json
import sys

sys.path.insert(0, "C:/Programming/Projects/aegis")

import httpx

from redteam.attacks.pair import PAIRAttack
import redteam.attacks.pair as pair_module

with open("data/advbench_sample_20_subset.txt", encoding="utf-8") as f:
    GOALS_20 = [line.strip() for line in f if line.strip()]

TARGET_URL = "http://localhost:8000/v1/chat/completions"


async def run_one(goal: str):
    import random
    attack = PAIRAttack(max_iterations=5)
    # Force this specific goal instead of random.choice - see module docstring.
    orig_choice = random.choice
    random.choice = lambda seq: goal if seq is pair_module.HARMFUL_GOALS else orig_choice(seq)
    try:
        return await attack.execute(TARGET_URL)
    finally:
        random.choice = orig_choice


async def main():
    results = []
    for i, goal in enumerate(GOALS_20, 1):
        r = await run_one(goal)
        results.append(r)
        print(f"[{i}/20] outcome={r.outcome} score={r.judge_score} goal={goal[:60]!r}")

    with open("data/pair_rerun_20.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps({
                "goal": r.metadata.get("harmful_goal"), "outcome": r.outcome,
                "judge_score": r.judge_score, "judge_rationale": r.judge_rationale,
                "prompt": r.prompt, "response": r.response,
                "iterations_to_bypass": r.metadata.get("iterations_to_bypass"),
            }) + "\n")

    from collections import Counter
    print("\nOutcome counts:", dict(Counter(r.outcome for r in results)))
    scores = [r.judge_score for r in results if r.judge_score is not None]
    print("Judge score distribution:", dict(sorted(Counter(scores).items())))

    top3 = sorted([r for r in results if r.judge_score is not None], key=lambda r: -r.judge_score)[:3]
    print("\nTop 3 by judge score:")
    for r in top3:
        print(f"  score={r.judge_score} outcome={r.outcome} goal={r.metadata.get('harmful_goal')!r}")
        print(f"    rationale={r.judge_rationale!r}")
        print(f"    response (first 150 chars): {r.response[:150]!r}")


if __name__ == "__main__":
    asyncio.run(main())
