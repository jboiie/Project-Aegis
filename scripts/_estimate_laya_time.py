import json
import time

import laya

agent = laya.load("convaiinnovations/laya", subfolder="typed-decisions", device="cpu")
gq = laya.guard_questions()

rows = [json.loads(l) for l in open("data/laya_screen_results.jsonl", encoding="utf-8")]
sample = [r for r in rows if r["split"] == "calibration" and r["blocking_layer"] in ("L1", "L2")][:20]

latencies = []
for r in sample:
    t0 = time.perf_counter()
    agent.predict({"text": r["prompt"]}, gq)
    latencies.append((time.perf_counter() - t0) * 1000)

latencies.sort()
n = len(latencies)
mean = sum(latencies) / n
print(f"n={n} mean={mean:.1f}ms p50={latencies[n//2]:.1f}ms max={max(latencies):.1f}ms")

for n_rows, label in [(1199, "calibration"), (1583, "sweep"), (1247, "test")]:
    est_s = n_rows * mean / 1000
    print(f"{label}: {n_rows} rows -> est {est_s:.0f}s ({est_s/60:.1f}min)")
total = (1199 + 1583 + 1247) * mean / 1000
print(f"TOTAL (all 3 splits): {total:.0f}s ({total/60:.1f}min)")
