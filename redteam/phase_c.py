"""
Phase C — PAIR (Prompt Automatic Iterative Refinement) Evaluation

Evaluates adaptive LLM-driven red-teaming (PAIR) against the full Aegis sandbox
guardrail stack.

Compares PAIR (adaptive, iterative) against fixed-corpus strategies (Template, Encoding).

Usage:
    python -m redteam.phase_c --target http://localhost:8000/v1/chat/completions --attempts 20 --max-iterations 5 --seed 42
"""

import asyncio
import argparse
import random

import structlog
from redteam.attacks.pair import PAIRAttack
from redteam.attacks.template import TemplateAttack
from redteam.attacks.encoding import EncodingAttack

logger = structlog.get_logger()


async def run_phase_c(target_url: str, attempts: int, max_iterations: int, seed: int):
    random.seed(seed)
    logger.info("phase_c_start", target=target_url, attempts=attempts, max_iterations=max_iterations, seed=seed)

    pair_attack = PAIRAttack(max_iterations=max_iterations)

    results = []
    bypasses = 0
    total_iterations_for_bypasses = 0

    print(f"\nRunning PAIR attack campaign ({attempts} goals, max {max_iterations} iterations each)...")

    for i in range(1, attempts + 1):
        print(f"Goal {i}/{attempts} running...", end="\r", flush=True)
        res = await pair_attack.execute(target_url)
        results.append(res)

        if res.bypassed:
            bypasses += 1
            iters = res.metadata.get("iterations_to_bypass", 1)
            total_iterations_for_bypasses += iters
            logger.info("pair_bypass", attempt=i, iterations=iters, goal=res.metadata.get("harmful_goal"))
        else:
            logger.info("pair_blocked", attempt=i, goal=res.metadata.get("harmful_goal"))

        await asyncio.sleep(1.0)

    asr = (bypasses / attempts) if attempts > 0 else 0.0
    avg_iters = (total_iterations_for_bypasses / bypasses) if bypasses > 0 else 0.0

    print("\n" + "=" * 50)
    print("PHASE C REPORT — PAIR vs. Aegis Full Stack")
    print("=" * 50)
    print(f"  target_url:                {target_url}")
    print(f"  attempts (goals):          {attempts}")
    print(f"  max_iterations_per_goal:   {max_iterations}")
    print(f"  successful_bypasses:       {bypasses}")
    print(f"  blocked:                   {attempts - bypasses}")
    print(f"  attack_success_rate (ASR): {asr:.2%}")
    print(f"  avg_iterations_to_bypass:  {avg_iters:.2f}")
    print("=" * 50)

    return {
        "attempts": attempts,
        "bypasses": bypasses,
        "asr": asr,
        "avg_iters": avg_iters,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aegis Phase C — PAIR Evaluation")
    parser.add_argument("--target", default="http://localhost:8000/v1/chat/completions")
    parser.add_argument("--attempts", type=int, default=20, help="Number of harmful goals to evaluate")
    parser.add_argument("--max-iterations", type=int, default=5, help="Max refinement steps per goal")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    asyncio.run(run_phase_c(args.target, args.attempts, args.max_iterations, args.seed))
