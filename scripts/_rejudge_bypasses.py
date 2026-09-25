import asyncio
import json
import sys

sys.path.insert(0, "C:/Programming/Projects/aegis")

import httpx

from redteam.judge import judge_response


async def main():
    bypasses = []
    for l in open("data/pair_rerun_20.jsonl", encoding="utf-8"):
        r = json.loads(l)
        if r["outcome"] == "bypassed":
            bypasses.append(r)

    async with httpx.AsyncClient(timeout=30.0) as client:
        for r in bypasses:
            score, rationale = await judge_response(client, r["goal"], r["response"])
            print(f"goal={r['goal']!r}")
            print(f"  OLD score={r['judge_score']}  NEW score={score}")
            print(f"  NEW rationale={rationale!r}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
