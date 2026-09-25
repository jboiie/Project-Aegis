import asyncio
import json
import sys
import time

sys.path.insert(0, "C:/Programming/Projects/aegis")

from src.guardrails.engine import GuardrailEngine


async def main():
    engine = GuardrailEngine()
    t0 = time.perf_counter()
    await engine.load_models()
    load_s = time.perf_counter() - t0
    print(f"Model load time: {load_s:.1f}s")

    # Sample real texts: mix of attack-set and benign rows already generated.
    texts = []
    for l in list(open("data/laya_attack_set.jsonl", encoding="utf-8"))[:30]:
        texts.append(json.loads(l)["prompt"])
    for l in list(open("data/benign_prompts.jsonl", encoding="utf-8"))[:20]:
        texts.append(json.loads(l)["prompt"])

    latencies = []
    for text in texts:
        t0 = time.perf_counter()
        await engine.screen(text, session_id=None)
        latencies.append((time.perf_counter() - t0) * 1000)

    latencies.sort()
    n = len(latencies)
    p50 = latencies[n // 2]
    p95 = latencies[int(n * 0.95)]
    mean = sum(latencies) / n
    print(f"n={n}  mean={mean:.1f}ms  p50={p50:.1f}ms  p95={p95:.1f}ms  max={max(latencies):.1f}ms")

    for n_rows, label in [(5500, "520 goals x 10 wrappers + 25 labeled + 300 benign"),
                           (2000, "150 goals x 10 wrappers + 25 labeled + 300 benign")]:
        est_mean_s = n_rows * mean / 1000
        est_p95_s = n_rows * p95 / 1000
        print(f"{label}: ~{n_rows} rows -> est {est_mean_s:.0f}s ({est_mean_s/60:.1f}min) at mean, "
              f"{est_p95_s:.0f}s ({est_p95_s/60:.1f}min) at p95-per-row worst case")


if __name__ == "__main__":
    asyncio.run(main())
