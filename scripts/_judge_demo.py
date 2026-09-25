"""Supplementary check, NOT part of the dry-run's official outcome tally:
the dry run's 28 attempts (8 PAIR x up to 5 iters + 10 template + 10
encoding) came back 100% blocked_by_stack, so redteam/judge.py was never
actually exercised against a real response. Rather than fabricate sample
judge verdicts, this sends the same real goals directly to the target
model (gpt-oss-120b), bypassing the sandbox's guardrail stack entirely
(simulating what a "guardrails off" ablation run would see), then judges
the real responses - genuine judge output, just not from the accounted
dry-run sample.
"""
import asyncio
import sys

sys.path.insert(0, "C:/Programming/Projects/aegis")

import httpx

from redteam.attacks.template import HARMFUL_REQUESTS
from redteam.judge import judge_response
from src.config import settings


async def main():
    goals = HARMFUL_REQUESTS[:5]
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for goal in goals:
            payload = {
                "model": settings.GROQ_MODEL,
                "messages": [{"role": "user", "content": goal}],
                "max_tokens": 300,
            }
            resp = await client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]

            score, rationale = await judge_response(client, goal, content)
            print(f"GOAL: {goal}")
            print(f"RESPONSE (first 200 chars): {content[:200]!r}")
            print(f"JUDGE: score={score}/10  rationale={rationale!r}")
            print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())
