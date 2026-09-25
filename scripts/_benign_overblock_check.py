import asyncio
import json
import sys
import uuid

sys.path.insert(0, "C:/Programming/Projects/aegis")

import httpx

from src.config import settings

TARGET_URL = "http://localhost:8000/v1/chat/completions"


async def main():
    with open("data/benign_prompts.jsonl", encoding="utf-8") as f:
        rows = [json.loads(l) for l in f]

    easy = [r for r in rows if r["difficulty"] == "easy"][:10]
    hard = [r for r in rows if r["difficulty"] == "hard"][:10]

    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for r in easy + hard:
            headers = {"X-Session-ID": str(uuid.uuid4())}
            payload = {"model": settings.GROQ_MODEL, "messages": [{"role": "user", "content": r["prompt"]}]}
            resp = await client.post(TARGET_URL, json=payload, headers=headers)
            data = resp.json()
            safety = data.get("safety") or {}
            blocked = bool(safety.get("blocked_reason"))
            failed = [c["name"] for c in safety.get("checks", []) if not c.get("passed", True)]
            results.append({**r, "blocked": blocked, "failed_checks": failed, "blocked_reason": safety.get("blocked_reason", "")})
            print(f"[{r['difficulty']}/{r['category']}] blocked={blocked} failed={failed} prompt={r['prompt'][:70]!r}")

    n_easy_blocked = sum(1 for r in results if r["difficulty"] == "easy" and r["blocked"])
    n_hard_blocked = sum(1 for r in results if r["difficulty"] == "hard" and r["blocked"])
    print(f"\nEasy blocked: {n_easy_blocked}/10")
    print(f"Hard blocked: {n_hard_blocked}/10")


if __name__ == "__main__":
    asyncio.run(main())
