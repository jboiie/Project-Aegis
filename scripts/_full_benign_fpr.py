import asyncio
import json
import sys
import uuid
from collections import defaultdict

sys.path.insert(0, "C:/Programming/Projects/aegis")

import httpx

from src.config import settings

TARGET_URL = "http://localhost:8000/v1/chat/completions"


async def main():
    with open("data/benign_prompts.jsonl", encoding="utf-8") as f:
        rows = [json.loads(l) for l in f]

    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for r in rows:
            headers = {"X-Session-ID": str(uuid.uuid4())}
            payload = {"model": settings.GROQ_MODEL, "messages": [{"role": "user", "content": r["prompt"]}]}
            resp = await client.post(TARGET_URL, json=payload, headers=headers)
            data = resp.json()
            safety = data.get("safety") or {}
            blocked = bool(safety.get("blocked_reason"))
            failed = [c["name"] for c in safety.get("checks", []) if not c.get("passed", True)]
            results.append({**r, "blocked": blocked, "failed_checks": failed})

    by_category = defaultdict(lambda: {"total": 0, "blocked": 0})
    for r in results:
        key = (r["difficulty"], r["category"])
        by_category[key]["total"] += 1
        if r["blocked"]:
            by_category[key]["blocked"] += 1

    print(f"Total benign prompts tested: {len(results)}\n")
    print(f"{'difficulty':<8} {'category':<28} {'blocked/total':<15} {'FPR':<8}")
    for (difficulty, category), counts in sorted(by_category.items()):
        fpr = counts["blocked"] / counts["total"] if counts["total"] else 0.0
        print(f"{difficulty:<8} {category:<28} {counts['blocked']}/{counts['total']:<13} {fpr:.1%}")

    total_blocked = sum(1 for r in results if r["blocked"])
    print(f"\nOverall FPR: {total_blocked}/{len(results)} = {total_blocked/len(results):.1%}")

    with open("data/full_benign_fpr_results.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    asyncio.run(main())
