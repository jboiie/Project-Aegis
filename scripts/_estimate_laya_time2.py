import inspect
import json
import time

import laya

agent = laya.load("convaiinnovations/laya", subfolder="typed-decisions", device="cpu")
gq_full = laya.guard_questions()
gq_2 = {k: gq_full[k] for k in ("jailbreak", "prompt_injection")}

print("predict_batch signature:", inspect.signature(agent.predict_batch))

rows = [json.loads(l) for l in open("data/laya_screen_results.jsonl", encoding="utf-8")]
sample = [r for r in rows if r["split"] == "calibration" and r["blocking_layer"] in ("L1", "L2")][:20]

# 2-question predict() timing
latencies = []
for r in sample:
    t0 = time.perf_counter()
    agent.predict({"text": r["prompt"]}, gq_2)
    latencies.append((time.perf_counter() - t0) * 1000)
latencies.sort()
n = len(latencies)
mean2q = sum(latencies) / n
print(f"\n2-question predict(): n={n} mean={mean2q:.1f}ms p50={latencies[n//2]:.1f}ms")

# batch timing, if predict_batch exists and works with list of states
try:
    states = [{"text": r["prompt"]} for r in sample]
    t0 = time.perf_counter()
    batch_result = agent.predict_batch(states, gq_2)
    batch_s = time.perf_counter() - t0
    print(f"\npredict_batch({len(states)} states, 2 questions): {batch_s*1000:.1f}ms total, "
          f"{batch_s*1000/len(states):.1f}ms/row")
    print("batch_result type:", type(batch_result), "len:", len(batch_result) if hasattr(batch_result, "__len__") else "?")
except Exception as e:
    print(f"\npredict_batch failed: {type(e).__name__}: {e}")

for n_rows, label in [(1199, "calibration"), (1583, "sweep"), (1247, "test")]:
    est_s = n_rows * mean2q / 1000
    print(f"{label} (2q serial): {n_rows} rows -> est {est_s:.0f}s ({est_s/60:.1f}min)")
total = (1199 + 1583 + 1247) * mean2q / 1000
print(f"TOTAL (2q serial, all 3 splits): {total:.0f}s ({total/60:.1f}min)")
