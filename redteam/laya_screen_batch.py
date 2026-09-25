"""Runs engine.screen() locally (no HTTP, no Groq) on the full attack set
and the full benign set, fresh session ID per row, cache off by
construction (GuardrailEngine() with no redis_cache = semantic_cache is
None). Saves per-row verdicts so laya_calibrate.py/laya_threshold_sweep.py/
laya_eval.py reuse this instead of re-running the stack.

Layer attribution: engine.py short-circuits on the first layer that fails
(L1/L2/L3), so the first check in SafetyVerdict.checks with passed=False
IS the blocking layer - no ambiguity. If nothing failed, the row passed
L1-L4 entirely (a PII-only failure at L4, if any, still shows up the same
way: pii_detection is the only failing check since L1-L3 already passed).
"""
import asyncio
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.guardrails.engine import GuardrailEngine

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ATTACK_SET_PATH = os.path.join(_REPO_ROOT, "data", "laya_attack_set.jsonl")
BENIGN_SET_PATH = os.path.join(_REPO_ROOT, "data", "benign_prompts.jsonl")
OUT_PATH = os.path.join(_REPO_ROOT, "data", "laya_screen_results.jsonl")

_LAYER_NAMES = {"regex_prefilter": "L1", "injection_detection": "L2",
                "toxicity_check": "L3", "pii_detection": "L4"}


def _blocking_layer(checks: list) -> str | None:
    for c in checks:
        if not c.passed:
            return _LAYER_NAMES.get(c.name, c.name)
    return None  # passed everything the stack ran


async def screen_row(engine: GuardrailEngine, text: str) -> dict:
    t0 = time.perf_counter()
    verdict = await engine.screen(text, session_id=str(uuid.uuid4()))
    latency_ms = (time.perf_counter() - t0) * 1000
    return {
        "blocked": not verdict.passed,
        "blocking_layer": _blocking_layer(verdict.checks),
        "blocked_reason": verdict.blocked_reason,
        "latency_ms": latency_ms,
    }


async def main():
    engine = GuardrailEngine()
    print("Loading models...")
    t0 = time.perf_counter()
    await engine.load_models()
    print(f"Loaded in {time.perf_counter()-t0:.1f}s")

    rows = []
    for l in open(ATTACK_SET_PATH, encoding="utf-8"):
        r = json.loads(l)
        r["row_type"] = "attack"
        rows.append(r)
    for l in open(BENIGN_SET_PATH, encoding="utf-8"):
        r = json.loads(l)
        r["row_type"] = "benign"
        rows.append(r)

    print(f"Screening {len(rows)} total rows ({sum(1 for r in rows if r['row_type']=='attack')} attack, "
          f"{sum(1 for r in rows if r['row_type']=='benign')} benign)...")

    results = []
    t_start = time.perf_counter()
    for i, row in enumerate(rows, 1):
        verdict = await screen_row(engine, row["prompt"])
        results.append({**row, **verdict})
        if i % 200 == 0:
            elapsed = time.perf_counter() - t_start
            rate = i / elapsed
            eta_s = (len(rows) - i) / rate
            print(f"  {i}/{len(rows)}  elapsed={elapsed:.0f}s  eta={eta_s:.0f}s ({eta_s/60:.1f}min)")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    total_s = time.perf_counter() - t_start
    print(f"\nDone in {total_s:.0f}s ({total_s/60:.1f}min). Written to {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
