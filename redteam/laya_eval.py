"""Final test-split report (step 5). Loads the TEST split only, applies
the threshold chosen by laya_threshold_sweep.py on the sweep split
(never re-derived from test data), and prints every table in the
step-5 spec (PROJECT_DESC.md's "Step 5 spec" section): FPR before/after
per benign category and batch group, strict/effective recall lost, the
end-to-end harm-check results, and Laya per-question latency - all with
Wilson 95% CIs.

Calibration wording (spec item 6): Laya's confidence is NEVER described
as calibrated anywhere in this output. The overturn decision is ranking
plus an empirically chosen threshold - see laya_calibrate.py's ECE
numbers for why: benign ECE is thin (n=7) and not something a single
scalar temperature can be trusted to fix.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def wilson_ci(x: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = x / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (max(0.0, center - margin), min(1.0, center + margin))


def fmt_rate(x: int, n: int) -> str:
    if n == 0:
        return "n/a"
    lo, hi = wilson_ci(x, n)
    return f"{x}/{n} = {x/n:.1%}  [{lo:.1%}, {hi:.1%}]"


def load_chosen_threshold() -> float:
    curve = [json.loads(l) for l in open(os.path.join(_REPO_ROOT, "data", "laya_threshold_sweep.jsonl"), encoding="utf-8")]
    chosen = [r for r in curve if r["chosen"]]
    if not chosen:
        raise RuntimeError("No threshold was chosen by laya_threshold_sweep.py - cannot run test eval.")
    return chosen[0]["t"]


def main():
    t = load_chosen_threshold()
    print(f"Fixed threshold from sweep split: t={t}\n")

    screen = [json.loads(l) for l in open(os.path.join(_REPO_ROOT, "data", "laya_screen_results.jsonl"), encoding="utf-8")]
    test_benign = [r for r in screen if r["row_type"] == "benign" and r["split"] == "test"]
    test_attack = [r for r in screen if r["row_type"] == "attack" and r["split"] == "test"]

    scores = [json.loads(l) for l in open(os.path.join(_REPO_ROOT, "data", "laya_scores_test.jsonl"), encoding="utf-8")]
    conf_by_prompt = {r["prompt"]: r["laya_confidence"] for r in scores}

    effective = [json.loads(l) for l in open(os.path.join(_REPO_ROOT, "data", "laya_effective_test.jsonl"), encoding="utf-8")]
    eff_by_prompt = {r["prompt"]: r["would_pass_l3_l4_outputguard"] for r in effective}

    # ---- Table 1: FPR before/after per benign category/batch group ----
    print("=" * 78)
    print("TABLE 1: FPR before/after Laya overturn (test split)")
    print("=" * 78)

    def group_fpr(rows: list[dict], label: str):
        n = len(rows)
        blocked = [r for r in rows if r["blocking_layer"] in ("L1", "L2")]
        n_blocked = len(blocked)
        overturned = [r for r in blocked if conf_by_prompt.get(r["prompt"], 0.0) >= t]
        n_overturned = len(overturned)
        n_after = n_blocked - n_overturned
        print(f"\n{label} (n={n}):")
        print(f"  FPR before: {fmt_rate(n_blocked, n)}")
        print(f"  Laya overturns: {n_overturned}/{n_blocked} blocked rows")
        print(f"  FPR after:  {fmt_rate(n_after, n)}")

    sec_ed_b12 = [r for r in test_benign if r["category"] == "security_education" and r.get("batch") in (1, 2)]
    sec_ed_b3 = [r for r in test_benign if r["category"] == "security_education" and r.get("batch") == 3]
    sec_ed_all = sec_ed_b12 + sec_ed_b3
    group_fpr(sec_ed_b12, "security_education, batches 1-2")
    group_fpr(sec_ed_b3, "security_education, batch 3 (template-generated - different distribution)")
    group_fpr(sec_ed_all, "security_education, COMBINED (headline)")

    literal = [r for r in test_benign if r["category"] == "literal_editing_instruction"]
    n_literal = len(literal)
    literal_blocked = [r for r in literal if r["blocking_layer"] in ("L1", "L2")]
    literal_overturned = [r for r in literal_blocked if conf_by_prompt.get(r["prompt"], 0.0) >= t]
    print(f"\nliteral_editing_instruction (n={n_literal}) - DESCRIPTIVE ONLY, no rate claimed (too few genuine rows):")
    print(f"  blocked: {len(literal_blocked)}/{n_literal}")
    print(f"  Laya overturns: {len(literal_overturned)}/{len(literal_blocked)} blocked rows")

    other = [r for r in test_benign if r["category"] not in ("security_education", "literal_editing_instruction")]
    group_fpr(other, "other 8 categories (all batch 1, expected near-zero)")

    # ---- Table 2: strict/effective recall lost ----
    print("\n" + "=" * 78)
    print("TABLE 2: strict/effective recall lost (test split attacks)")
    print("=" * 78)
    attack_blocked = [r for r in test_attack if r["blocking_layer"] in ("L1", "L2")]
    n_attack = len(attack_blocked)
    strict_overturned = [r for r in attack_blocked if conf_by_prompt.get(r["prompt"], 0.0) >= t]
    effective_overturned = [r for r in strict_overturned if eff_by_prompt.get(r["prompt"], False)]
    print(f"\nAttacks L1/L2 blocked (test): {n_attack}")
    print(f"  strict recall lost:    {fmt_rate(len(strict_overturned), n_attack)}")
    print(f"  effective recall lost: {fmt_rate(len(effective_overturned), n_attack)}")

    # ---- Table 3: end-to-end harm check ----
    print("\n" + "=" * 78)
    print("TABLE 3: end-to-end harm check (Laya-overturned test attacks, qwen/qwen3.8-27b)")
    print("=" * 78)
    harm_path = os.path.join(_REPO_ROOT, "data", "laya_harm_check.jsonl")
    if os.path.exists(harm_path):
        harm = [json.loads(l) for l in open(harm_path, encoding="utf-8")]
        n_harm = len(harm)
        for outcome in ("refused_by_model", "bypassed", "errored", "blocked_by_stack"):
            n_o = sum(1 for r in harm if r["outcome"] == outcome)
            if n_o or outcome in ("refused_by_model", "bypassed", "errored"):
                print(f"  {outcome:<18} {fmt_rate(n_o, n_harm)}")
        bypasses = [r for r in harm if r["outcome"] == "bypassed"]
        if bypasses:
            print(f"\n  {len(bypasses)} BYPASS(ES) - full detail:")
            for r in bypasses:
                print(f"\n  --- prompt ---\n  {r['prompt']}")
                print(f"  --- response ---\n  {r['response']}")
                print(f"  --- judge (score={r['judge_score']}) ---\n  {r['judge_rationale']}")
    else:
        print("  data/laya_harm_check.jsonl not found - run redteam/laya_harm_check.py first.")

    # ---- Table 4: Laya latency ----
    print("\n" + "=" * 78)
    print("TABLE 4: Laya per-question latency (this run)")
    print("=" * 78)
    latency_path = os.path.join(_REPO_ROOT, "data", "laya_latency_test.json")
    if os.path.exists(latency_path):
        with open(latency_path, encoding="utf-8") as f:
            lat = json.load(f)
        print(f"  n={lat['n']}  p50={lat['p50_ms']:.1f}ms  p95={lat['p95_ms']:.1f}ms  "
              f"(2-question predict() call, fp32 CPU)")
    else:
        print("  data/laya_latency_test.json not found - run scripts/_measure_laya_latency.py first.")

    print("\n" + "=" * 78)
    print("CALIBRATION WORDING (spec item 6)")
    print("=" * 78)
    with open(os.path.join(_REPO_ROOT, "data", "laya_calibration.json"), encoding="utf-8") as f:
        cal = json.load(f)
    print(f"  T={cal['temperature']}, fit on calibration split (class-balanced weighting, "
          f"n_attack={cal['n_attack']}, n_benign={cal['n_benign']})")
    print(f"  ECE before: combined={cal['ece_before']['ece_combined']:.4f} "
          f"attack={cal['ece_before']['ece_attack']:.4f} benign={cal['ece_before']['ece_benign']:.4f}")
    print(f"  ECE after:  combined={cal['ece_after']['ece_combined']:.4f} "
          f"attack={cal['ece_after']['ece_attack']:.4f} benign={cal['ece_after']['ece_benign']:.4f}")
    print("  Laya's confidence is NOT described as calibrated anywhere in this report.")
    print("  The overturn decision relies on RANKING plus an empirically chosen")
    print("  threshold (t, fit on the sweep split's attack recall constraint only),")
    print("  not on the confidence value being a trustworthy probability.")


if __name__ == "__main__":
    main()
