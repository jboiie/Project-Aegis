"""Phase 0 benchmark, v2: Laya (laya-typed-decisions, CPU) vs Aegis's own L2
DeBERTa injection detector and OutputGuard, all on the same real inputs, on
this machine, with the methodology fixes the user requested after v1:
  - per-question latency (guard_questions() sends 5 questions/call, plus
    our 1 noul question = 6 questions/call), not just per-call
  - first 5 calls excluded as warm-up
  - torch thread count, dtype, and AC-power state reported (battery vs
    plugged in changes CPU clocking on a laptop, and this machine's v1 runs
    varied call-to-call - AC state is a real candidate cause, not noise)
  - fp32 and bf16 both tried on CPU (no dtype kwarg on laya.load/Agent, so
    this manually casts agent.model after load)
  - 3 full runs, spread reported, not a single number
Every latency number in the plan traces to THIS script's output.
"""
import json
import os
import sys
import time

import psutil
import torch

sys.path.insert(0, r"C:/Programming/Projects/aegis")

AEGIS_DIR = r"C:/Programming/Projects/aegis"
LABELED_SET = os.path.join(AEGIS_DIR, "data", "labeled_eval_set.jsonl")
AGENT_ANSWERS = os.path.join(AEGIS_DIR, "scripts", "laya_bench_agent_answers.json")
WARMUP_CALLS = 5
N_RUNS = 3


def rss_mb() -> float:
    return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)


def percentile(values: list[float], p: float) -> float:
    s = sorted(values)
    k = (len(s) - 1) * p
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def power_state() -> str:
    b = psutil.sensors_battery()
    if b is None:
        return "unknown (no battery sensor - likely desktop, treat as AC)"
    return "AC (plugged in)" if b.power_plugged else f"BATTERY ({b.percent}% remaining)"


def load_inputs() -> list[dict]:
    rows = []
    with open(LABELED_SET, encoding="utf-8") as f:
        labeled = [json.loads(line) for line in f]
    attacks = [r for r in labeled if r["label"] == "attack"][:5]
    benign = [r for r in labeled if r["label"] == "benign"][:5]
    for r in attacks + benign:
        rows.append({"text": r["prompt"], "label": r["label"], "source": "aegis_labeled_set"})

    if os.path.exists(AGENT_ANSWERS):
        with open(AGENT_ANSWERS, encoding="utf-8") as f:
            agent_answers = json.load(f)
        for a in agent_answers:
            rows.append({"text": a["answer"], "label": None, "source": f"argus_agent_{a['kind']}"})
    return rows


def _run_laya_once(inputs: list[dict], dtype: str) -> dict:
    import laya
    t0 = time.perf_counter()
    agent = laya.load("convaiinnovations/laya", subfolder="typed-decisions", device="cpu")
    if dtype == "bf16":
        agent.model = agent.model.to(torch.bfloat16)
    load_s = time.perf_counter() - t0

    guard_q = laya.guard_questions()
    noul_q = {"policy_violation": {"type": "noul", "instructions": "Does this text violate stated policy or make an unsupported claim?"}}
    n_questions_per_call = len(guard_q) + len(noul_q)

    call_latencies = []
    for row in inputs:
        state = {"text": row["text"]}
        t0 = time.perf_counter()
        agent.predict(state, guard_q)
        agent.predict(state, noul_q)
        call_latencies.append((time.perf_counter() - t0) * 1000)

    del agent
    warm = call_latencies[WARMUP_CALLS:] if len(call_latencies) > WARMUP_CALLS else call_latencies
    per_question = [c / n_questions_per_call for c in warm]

    return {
        "load_time_s": load_s,
        "n_questions_per_call": n_questions_per_call,
        "call_p50_ms": percentile(warm, 0.5),
        "call_p95_ms": percentile(warm, 0.95),
        "per_question_p50_ms": percentile(per_question, 0.5),
        "per_question_p95_ms": percentile(per_question, 0.95),
        "n_calls_after_warmup": len(warm),
    }


def bench_laya_all(inputs: list[dict]) -> dict:
    results = {"fp32": [], "bf16": [], "bf16_error": None}
    for dtype in ("fp32", "bf16"):
        for run_i in range(N_RUNS):
            print(f"    laya [{dtype}] run {run_i+1}/{N_RUNS}...")
            try:
                results[dtype].append(_run_laya_once(inputs, dtype))
            except Exception as exc:
                # bf16: naive whole-model .to(bfloat16) leaves some internal
                # buffers in fp32 (no public dtype kwarg on laya.load/Agent
                # to do this properly) - real, reproducible library
                # limitation, not a transient failure. Record once, stop
                # retrying bf16, keep fp32 results intact.
                msg = f"{type(exc).__name__}: {exc}"
                print(f"    laya [{dtype}] FAILED: {msg}")
                results["bf16_error"] = msg
                break
    return results


def _run_deberta_once(inputs: list[dict]) -> dict:
    import asyncio
    from src.guardrails.injection import InjectionDetector

    detector = InjectionDetector()
    t0 = time.perf_counter()
    asyncio.run(detector.load())
    load_s = time.perf_counter() - t0

    latencies = []
    for row in inputs:
        t0 = time.perf_counter()
        asyncio.run(detector.check(row["text"]))
        latencies.append((time.perf_counter() - t0) * 1000)

    warm = latencies[WARMUP_CALLS:] if len(latencies) > WARMUP_CALLS else latencies
    return {
        "load_time_s": load_s,
        "p50_ms": percentile(warm, 0.5),
        "p95_ms": percentile(warm, 0.95),
        "n_calls_after_warmup": len(warm),
    }


def bench_deberta_all(inputs: list[dict]) -> list[dict]:
    results = []
    for run_i in range(N_RUNS):
        print(f"    deberta L2 run {run_i+1}/{N_RUNS}...")
        results.append(_run_deberta_once(inputs))
    return results


def bench_outputguard(inputs: list[dict]) -> dict:
    from src.guardrails.output import OutputGuard
    guard = OutputGuard()
    latencies = []
    for row in inputs:
        t0 = time.perf_counter()
        guard.screen_output(row["text"])
        latencies.append((time.perf_counter() - t0) * 1000)
    warm = latencies[WARMUP_CALLS:] if len(latencies) > WARMUP_CALLS else latencies
    return {"p50_ms": percentile(warm, 0.5), "p95_ms": percentile(warm, 0.95)}


def token_length_check():
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained("answerdotai/ModernBERT-large")
    if not os.path.exists(AGENT_ANSWERS):
        return None
    with open(AGENT_ANSWERS, encoding="utf-8") as f:
        answers = json.load(f)
    lengths = [len(tok.encode(a["answer"])) for a in answers]
    p95_answer_tokens = percentile(lengths, 0.95)
    refund_claims = [
        "Items can be returned for a refund within 30 days of delivery.",
        "A valid order ID is required to process any refund.",
        "Items purchased during a clearance sale are not eligible for refund, only exchange.",
        "Approved refunds are credited to the original payment method within 5-7 business days.",
    ]
    claims_tokens = len(tok.encode(" ".join(refund_claims)))
    question_tokens = len(tok.encode("What is your refund policy?"))
    worst_case_total = claims_tokens + question_tokens + p95_answer_tokens
    return {
        "n_answers": len(answers),
        "p50_answer_tokens": percentile(lengths, 0.5),
        "p95_answer_tokens": p95_answer_tokens,
        "max_answer_tokens": max(lengths),
        "worst_case_cascade_state_tokens": worst_case_total,
        "fits_768_budget": worst_case_total <= 768,
        "fits_320_budget_english_checkpoint": worst_case_total <= 320,
    }


def main():
    print(f"torch.get_num_threads(): {torch.get_num_threads()}")
    print(f"Power state: {power_state()}")
    print("Loading benchmark inputs...")
    inputs = load_inputs()
    print(f"  {len(inputs)} inputs loaded (warm-up excludes first {WARMUP_CALLS} per run)\n")

    print("=" * 60)
    print(f"LAYA (laya-typed-decisions, CPU) - {N_RUNS} runs x 2 dtypes")
    print("=" * 60)
    laya_results = bench_laya_all(inputs)
    for dtype in ("fp32", "bf16"):
        runs = laya_results[dtype]
        if not runs:
            print(f"\n  dtype={dtype}: no results - {laya_results.get('bf16_error', 'unknown failure')}")
            continue
        p50s = [r["call_p50_ms"] for r in runs]
        p95s = [r["call_p95_ms"] for r in runs]
        pq50s = [r["per_question_p50_ms"] for r in runs]
        pq95s = [r["per_question_p95_ms"] for r in runs]
        print(f"\n  dtype={dtype}, {runs[0]['n_questions_per_call']} questions/call")
        print(f"    per-CALL p50 across {N_RUNS} runs: {p50s} -> spread {min(p50s):.1f}-{max(p50s):.1f}ms")
        print(f"    per-CALL p95 across {N_RUNS} runs: {p95s} -> spread {min(p95s):.1f}-{max(p95s):.1f}ms")
        print(f"    per-QUESTION p50 across {N_RUNS} runs: {[f'{v:.1f}' for v in pq50s]}ms")
        print(f"    per-QUESTION p95 across {N_RUNS} runs: {[f'{v:.1f}' for v in pq95s]}ms")
        load_times_str = [f"{r['load_time_s']:.1f}s" for r in runs]
        print(f"    load times: {load_times_str}")

    print("\n" + "=" * 60)
    print(f"AEGIS L2 - DeBERTa injection detector - {N_RUNS} runs")
    print("=" * 60)
    l2_results = bench_deberta_all(inputs)
    p50s = [r["p50_ms"] for r in l2_results]
    p95s = [r["p95_ms"] for r in l2_results]
    print(f"  p50 across {N_RUNS} runs: {[f'{v:.1f}' for v in p50s]}ms -> spread {min(p50s):.1f}-{max(p50s):.1f}ms")
    print(f"  p95 across {N_RUNS} runs: {[f'{v:.1f}' for v in p95s]}ms -> spread {min(p95s):.1f}-{max(p95s):.1f}ms")

    print("\n" + "=" * 60)
    print("AEGIS OutputGuard - regex-only")
    print("=" * 60)
    og_result = bench_outputguard(inputs)
    print(f"  p50: {og_result['p50_ms']:.3f}ms  p95: {og_result['p95_ms']:.3f}ms")

    print("\n" + "=" * 60)
    print("TOKEN BUDGET CHECK")
    print("=" * 60)
    tok_result = token_length_check()
    if tok_result:
        print(f"  n={tok_result['n_answers']}  p50={tok_result['p50_answer_tokens']:.0f} p95={tok_result['p95_answer_tokens']:.0f} max={tok_result['max_answer_tokens']}")
        print(f"  worst-case cascade state: {tok_result['worst_case_cascade_state_tokens']:.0f} tokens, fits 768: {tok_result['fits_768_budget']}, fits 320: {tok_result['fits_320_budget_english_checkpoint']}")

    all_results = {
        "torch_num_threads": torch.get_num_threads(),
        "power_state": power_state(),
        "laya": laya_results,
        "deberta_l2": l2_results,
        "outputguard": og_result,
        "token_budget": tok_result,
        "n_inputs": len(inputs),
    }
    out_path = os.path.join(AEGIS_DIR, "scripts", "laya_bench_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nFull results written to {out_path}")


if __name__ == "__main__":
    main()
