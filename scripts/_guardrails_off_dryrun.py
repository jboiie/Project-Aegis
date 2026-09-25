"""Guardrails-off dry run: same 28 attacks (8 PAIR, 10 template, 10
encoding), same judge, but the target call goes DIRECTLY to Groq instead of
through the sandbox - the sandbox's own startup probe correctly refuses to
boot with all layers disabled (asserts L1 actually blocks a known attack),
so bypassing the stack entirely at the network level is the faithful way to
simulate "guardrails off" without weakening a real safety check. Since
there's no [BLOCKED] marker possible here, every response reaches the
judge - "blocked_by_stack" can never occur by construction, matching a
true zero-guardrail baseline.
"""
import asyncio
import json
import random
import sys

sys.path.insert(0, "C:/Programming/Projects/aegis")

import httpx

from redteam.attacks.template import TEMPLATES, HARMFUL_REQUESTS
from redteam.attacks.encoding import ENCODERS, BASE_PROMPTS
from redteam.attacks.pair import HARMFUL_GOALS, _generate_attacker_prompt
from redteam.judge import is_compliant, judge_response
from src.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


async def call_target(client, content):
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": settings.GROQ_MODEL, "messages": [{"role": "user", "content": content}], "max_tokens": 1024}
    resp = await client.post(GROQ_URL, json=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


async def run_single_shot(client, content, goal_for_judge, strategy):
    response = await call_target(client, content)
    score, rationale = await judge_response(client, goal_for_judge, response)
    outcome = "bypassed" if is_compliant(score) else "refused_by_model"
    return {"strategy": strategy, "prompt": content, "response": response, "outcome": outcome,
            "judge_score": score, "judge_rationale": rationale}


async def run_pair(client, max_iterations=5):
    goal = random.choice(HARMFUL_GOALS)
    history = []
    for iteration in range(1, max_iterations + 1):
        candidate, _ = await _generate_attacker_prompt(client=client, goal=goal, history=history)
        response = await call_target(client, candidate)
        score, rationale = await judge_response(client, goal, response)
        if is_compliant(score):
            return {"strategy": "pair", "prompt": candidate, "response": response, "outcome": "bypassed",
                    "judge_score": score, "judge_rationale": rationale, "iterations_to_bypass": iteration}
        history.append({"prompt": candidate, "response": f"{response}\n[Judge: not compliant, score={score}/10]"})
    return {"strategy": "pair", "prompt": candidate, "response": response, "outcome": "refused_by_model",
            "judge_score": score, "judge_rationale": rationale, "iterations_to_bypass": None}


async def main():
    random.seed(42)
    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=== TEMPLATE (10, guardrails off) ===")
        for i in range(10):
            template = random.choice(TEMPLATES)
            harmful = random.choice(HARMFUL_REQUESTS)
            prompt = template["prompt"].format(harmful_request=harmful)
            r = await run_single_shot(client, prompt, harmful, "template")
            results.append(r)
            print(f"  [{r['outcome']}] score={r['judge_score']} {template['name']}")

        print("\n=== ENCODING (10, guardrails off) ===")
        for i in range(10):
            base_prompt = random.choice(BASE_PROMPTS)
            encoding_name = random.choice(list(ENCODERS.keys()))
            encoded = ENCODERS[encoding_name](base_prompt)
            r = await run_single_shot(client, encoded, base_prompt, "encoding")
            results.append(r)
            print(f"  [{r['outcome']}] score={r['judge_score']} {encoding_name}")

        print("\n=== PAIR (8, guardrails off) ===")
        for i in range(8):
            r = await run_pair(client)
            results.append(r)
            print(f"  [{r['outcome']}] score={r['judge_score']} iters={r['iterations_to_bypass']}")

    with open("data/dryrun_guardrails_off.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    from collections import Counter
    print("\nOutcome counts:", dict(Counter(r["outcome"] for r in results)))
    non_refusals = [r for r in results if r["outcome"] == "bypassed"]
    print(f"\n{len(non_refusals)} bypassed (score>=10). Sample verdicts:")
    for r in non_refusals[:3]:
        print(f"  strategy={r['strategy']} score={r['judge_score']} rationale={r['judge_rationale']!r}")
        print(f"    response (first 150 chars): {r['response'][:150]!r}")


if __name__ == "__main__":
    asyncio.run(main())
