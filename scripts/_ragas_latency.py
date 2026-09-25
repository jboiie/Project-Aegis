"""RAGAS Faithfulness latency on the same real Argus faithfulness Q&A pairs
laya_bench.py measures Laya against - this is the comparison the cascade
headline (LLM calls saved, latency saved) actually depends on, and it was
never measured in Phase 0 v1. Run in the argus conda env (ragas/openai live
there, not in laya-bench).
"""
import asyncio
import json
import sys
import time

sys.path.insert(0, r"C:/Programming/Projects/argus")

from drift.diff import check_faithfulness

AGENT_ANSWERS = r"C:/Programming/Projects/aegis/scripts/laya_bench_agent_answers.json"
POLICIES = r"C:/Programming/Projects/argus/policies.json"
OUT_PATH = r"C:/Programming/Projects/aegis/scripts/ragas_latency_results.json"


async def main():
    with open(AGENT_ANSWERS, encoding="utf-8") as f:
        answers = json.load(f)
    with open(POLICIES, encoding="utf-8") as f:
        policies = json.load(f)

    topics = {}
    for p in policies:
        topics.setdefault(p["topic"], []).append(p)

    faithfulness_answers = [a for a in answers if a["kind"] == "faithfulness"]
    print(f"Running RAGAS Faithfulness on {len(faithfulness_answers)} real faithfulness Q&A pairs...")

    results = []
    for a in faithfulness_answers:
        # question is "What is your <topic> policy?" - matches drift/sampler.py's construction
        topic = a["question"].replace("What is your ", "").replace(" policy?", "")
        claims = topics.get(topic, [])
        if not claims:
            print(f"  (skip: couldn't map question {a['question']!r} to a topic)")
            continue
        context = [c["claim"] for c in claims]
        for claim in claims:
            t0 = time.perf_counter()
            status = "ok"
            try:
                result = await check_faithfulness(a["question"], claim["id"], claim["claim"], a["answer"], context_claims=context)
                if result.check_status == "errored":
                    status = "errored"
            except Exception as exc:
                status = f"failed: {type(exc).__name__}: {exc}"
            latency_ms = (time.perf_counter() - t0) * 1000
            results.append({"topic": topic, "claim_id": claim["id"], "status": status, "latency_ms": latency_ms})
            print(f"  [{status}] {topic}/{claim['id']}: {latency_ms:.0f}ms")

    ok = [r["latency_ms"] for r in results if r["status"] == "ok"]
    failed = [r for r in results if r["status"] != "ok"]
    print(f"\n{len(ok)}/{len(results)} succeeded, {len(failed)} errored/failed")
    if ok:
        s = sorted(ok)
        print(f"  latency: min={s[0]:.0f}ms max={s[-1]:.0f}ms median={s[len(s)//2]:.0f}ms")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"results": results, "n_ok": len(ok), "n_failed": len(failed)}, f, indent=2)
    print(f"Written to {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
