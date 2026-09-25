"""Measures Laya's per-question latency on a sample of test-split rows,
same 2-question predict() call laya_second_stage.py uses. Run AFTER
laya_score_split.py --split test finishes (avoid CPU contention from
two concurrent Laya processes skewing both timings).
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import laya

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N_SAMPLE = 50

agent = laya.load("convaiinnovations/laya", subfolder="typed-decisions", device="cpu")
gq_full = laya.guard_questions()
gq = {k: gq_full[k] for k in ("jailbreak", "prompt_injection")}

rows = [json.loads(l) for l in open(os.path.join(_REPO_ROOT, "data", "laya_screen_results.jsonl"), encoding="utf-8")]
sample = [r for r in rows if r["split"] == "test" and r["blocking_layer"] in ("L1", "L2")][:N_SAMPLE]

# each predict() call answers 2 questions - latency per question, not per call
call_latencies = []
for r in sample:
    t0 = time.perf_counter()
    agent.predict({"text": r["prompt"]}, gq)
    call_latencies.append((time.perf_counter() - t0) * 1000)

per_question = [c / len(gq) for c in call_latencies]
per_question.sort()
n = len(per_question)
p50 = per_question[n // 2]
p95 = per_question[int(n * 0.95)] if n > 1 else per_question[0]

out = {"n": n, "p50_ms": p50, "p95_ms": p95, "n_questions_per_call": len(gq)}
with open(os.path.join(_REPO_ROOT, "data", "laya_latency_test.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print(f"n={n}  p50={p50:.1f}ms  p95={p95:.1f}ms")
