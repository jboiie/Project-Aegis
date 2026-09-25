"""Screens only the new batch-3 benign rows (200 rows, split=test) with
engine.screen(), cache off, fresh session per row, no Groq calls, and
appends them to the existing data/laya_screen_results.jsonl so it stays
the single source of truth for all downstream steps.
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
BENIGN_SET_PATH = os.path.join(_REPO_ROOT, "data", "benign_prompts.jsonl")
RESULTS_PATH = os.path.join(_REPO_ROOT, "data", "laya_screen_results.jsonl")

_LAYER_NAMES = {"regex_prefilter": "L1", "injection_detection": "L2",
                "toxicity_check": "L3", "pii_detection": "L4"}


def _blocking_layer(checks: list) -> str | None:
    for c in checks:
        if not c.passed:
            return _LAYER_NAMES.get(c.name, c.name)
    return None


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
    for l in open(BENIGN_SET_PATH, encoding="utf-8"):
        r = json.loads(l)
        if r.get("batch") == 3:
            r["row_type"] = "benign"
            rows.append(r)

    print(f"Screening {len(rows)} batch-3 benign rows...")

    results = []
    t_start = time.perf_counter()
    for i, row in enumerate(rows, 1):
        verdict = await screen_row(engine, row["prompt"])
        results.append({**row, **verdict})
        if i % 50 == 0:
            print(f"  {i}/{len(rows)}")

    with open(RESULTS_PATH, "a", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    total_s = time.perf_counter() - t_start
    print(f"\nDone in {total_s:.0f}s. Appended {len(results)} rows to {RESULTS_PATH}")
    n_blocked = sum(1 for r in results if r["blocking_layer"] in ("L1", "L2"))
    print(f"batch3 blocked by L1/L2: {n_blocked}/{len(results)}")


if __name__ == "__main__":
    asyncio.run(main())
