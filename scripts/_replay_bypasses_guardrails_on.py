import asyncio
import json
import sys
import uuid

sys.path.insert(0, "C:/Programming/Projects/aegis")

import httpx

from src.config import settings

TARGET_URL = "http://localhost:8000/v1/chat/completions"

bypass_prompts = []
for l in open("data/pair_rerun_20.jsonl", encoding="utf-8"):
    r = json.loads(l)
    if r["outcome"] == "bypassed":
        bypass_prompts.append((r["goal"], r["prompt"]))


async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        for goal, prompt in bypass_prompts:
            headers = {"X-Session-ID": str(uuid.uuid4())}
            payload = {"model": settings.GROQ_MODEL, "messages": [{"role": "user", "content": prompt}]}
            resp = await client.post(TARGET_URL, json=payload, headers=headers)
            data = resp.json()
            safety = data.get("safety") or {}
            blocked = bool(safety.get("blocked_reason"))
            failed = [c["name"] for c in safety.get("checks", []) if not c.get("passed", True)]
            print(f"goal={goal!r}")
            print(f"  blocked={blocked}  failed_checks={failed}  reason={safety.get('blocked_reason', '')!r}")
            if not blocked:
                print(f"  PASSED THE STACK - content: {data.get('content', '')[:150]!r}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
